"""The assistant brain.

`Brain.respond_stream()` yields spoken-ready sentence chunks. With an OpenAI
key configured it runs a streaming tool-calling loop with conversation
memory; without one it falls back to the offline keyword router so basic
commands still work.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator

from mythos import router, tools
from mythos.config import Config
from mythos.tools.memory_tools import get_memory

# Split after sentence-ending punctuation (optionally followed by a closing
# quote/bracket), consuming only the whitespace so the punctuation is kept.
_SENTENCE_END = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"')\]]))\s+")
_MAX_TOOL_ROUNDS = 6
_MAX_HISTORY_MESSAGES = 40


def split_sentences(buffer: str) -> tuple[list[str], str]:
    """Split completed sentences off the front of a streaming text buffer.

    Returns (complete_sentences, remainder).
    """
    parts = _SENTENCE_END.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    complete = [p.strip() for p in parts[:-1] if p.strip()]
    return complete, parts[-1]


class Brain:
    def __init__(self, config: Config):
        self.config = config
        self._client = None
        self.history: list[dict] = []

    # ------------------------------------------------------------------
    def _system_prompt(self) -> str:
        facts = get_memory().all_facts()
        prompt = (
            f"You are {self.config.assistant_name}, a highly capable voice assistant. "
            "Your replies are spoken aloud, so keep them concise and conversational — "
            "no markdown, no bullet points, no URLs read letter by letter. "
            "Use your tools whenever they can accomplish the user's request. "
            "If a request needs information you don't have (like an email recipient), "
            "ask a short follow-up question instead of guessing. "
            "When the user shares a lasting preference or personal fact, store it "
            "with remember_fact."
        )
        if facts:
            prompt += "\n\nThings you remember about the user:\n- " + "\n- ".join(facts[:20])
        return prompt

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.config.openai_api_key)
        return self._client

    def _trim_history(self) -> None:
        if len(self.history) > _MAX_HISTORY_MESSAGES:
            # Drop oldest turns, but never split a tool-call/result pair:
            # advance the cut past any leading tool results.
            cut = len(self.history) - _MAX_HISTORY_MESSAGES
            while cut < len(self.history) and self.history[cut].get("role") == "tool":
                cut += 1
            self.history = self.history[cut:]

    # ------------------------------------------------------------------
    async def respond_stream(self, user_text: str) -> AsyncIterator[str]:
        """Yield sentence-sized chunks of the reply as they become available."""
        if not self.config.has_openai:
            yield await asyncio.to_thread(self._fallback_respond, user_text)
            return

        self.history.append({"role": "user", "content": user_text})
        self._trim_history()
        messages = [{"role": "system", "content": self._system_prompt()}, *self.history]
        client = self._get_client()

        for _ in range(_MAX_TOOL_ROUNDS):
            stream = await client.chat.completions.create(
                model=self.config.openai_model,
                messages=messages,
                tools=tools.schemas() or None,
                stream=True,
            )

            buffer = ""
            full_text = ""
            tool_calls: dict[int, dict] = {}
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue
                if delta.content:
                    buffer += delta.content
                    full_text += delta.content
                    complete, buffer = split_sentences(buffer)
                    for sentence in complete:
                        yield sentence
                for tc in delta.tool_calls or []:
                    entry = tool_calls.setdefault(
                        tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        entry["id"] = tc.id
                    if tc.function and tc.function.name:
                        entry["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        entry["arguments"] += tc.function.arguments

            if buffer.strip():
                yield buffer.strip()

            if not tool_calls:
                if full_text:
                    self.history.append({"role": "assistant", "content": full_text})
                return

            # Execute the requested tools, then loop for the follow-up reply.
            assistant_msg = {
                "role": "assistant",
                "content": full_text or None,
                "tool_calls": [
                    {"id": e["id"], "type": "function",
                     "function": {"name": e["name"], "arguments": e["arguments"]}}
                    for e in tool_calls.values()
                ],
            }
            messages.append(assistant_msg)
            self.history.append(assistant_msg)
            for entry in tool_calls.values():
                try:
                    args = json.loads(entry["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await asyncio.to_thread(tools.dispatch, entry["name"], args)
                tool_msg = {"role": "tool", "tool_call_id": entry["id"], "content": result}
                messages.append(tool_msg)
                self.history.append(tool_msg)

        yield "I got stuck in a tool loop, sir. Could you rephrase that?"

    async def respond(self, user_text: str) -> str:
        """Convenience: full reply as a single string."""
        parts = [chunk async for chunk in self.respond_stream(user_text)]
        return " ".join(parts)

    # ------------------------------------------------------------------
    def _fallback_respond(self, user_text: str) -> str:
        call = router.route(user_text)
        if call is not None:
            return tools.dispatch(call.name, call.arguments)
        return ("I can handle that better with an OpenAI key configured. "
                "For now I can do things like time, weather, news, Wikipedia, "
                "music, volume, and brightness.")
