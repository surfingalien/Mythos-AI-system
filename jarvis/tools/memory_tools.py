"""Memory tools: let the assistant remember and recall facts across sessions."""

from __future__ import annotations

from jarvis.config import config
from jarvis.memory import Memory
from jarvis.tools.registry import tool

_memory: Memory | None = None


def get_memory() -> Memory:
    global _memory
    if _memory is None:
        _memory = Memory(config.memory_path)
    return _memory


@tool(
    description="Store a fact about the user or their preferences for future sessions "
                "(e.g. 'The user's favorite city is Tokyo').",
    parameters={"fact": {"type": "string", "description": "The fact to remember"}},
)
def remember_fact(fact: str) -> str:
    get_memory().remember(fact)
    return "Noted. I'll remember that."


@tool(
    description="Search remembered facts about the user.",
    parameters={"query": {"type": "string", "description": "What to look for"}},
)
def recall_facts(query: str) -> str:
    hits = get_memory().search(query)
    if not hits:
        return "I don't have anything remembered about that."
    return "Here's what I remember: " + " | ".join(hits[:5])


@tool(
    description="Forget remembered facts containing the given text.",
    parameters={"text": {"type": "string", "description": "Text identifying facts to forget"}},
)
def forget_fact(text: str) -> str:
    n = get_memory().forget(text)
    return f"Forgot {n} fact(s)." if n else "Nothing matched that."
