"""The async assistant pipeline.

Flow: wake word -> listen -> LLM (streaming) -> speak, with barge-in:
saying the wake word while Jarvis is talking interrupts the reply and
starts listening again immediately.

Blocking audio calls (mic capture, wake detection) run in worker threads;
the pipeline itself is a single asyncio task, which keeps it interruptible
and easy to reason about.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable

from jarvis.audio.stt import STT
from jarvis.audio.tts import TTS
from jarvis.audio.wake import WakeWordDetector
from jarvis.config import Config
from jarvis.llm import Brain

LogFn = Callable[[str, str], None]
StatusFn = Callable[[str], None]


class Pipeline:
    def __init__(self, config: Config,
                 on_log: LogFn | None = None,
                 on_status: StatusFn | None = None):
        self.config = config
        self.on_log = on_log or (lambda who, text: print(f"{who}: {text}"))
        self.on_status = on_status or (lambda status: None)
        self.stop_event = threading.Event()

        self.brain = Brain(config)
        self.tts = TTS(config)
        self.stt = STT(config)
        self.wake = WakeWordDetector(config, stt=self.stt)

    def request_stop(self) -> None:
        """Thread-safe stop request (used by the GUI Stop button)."""
        self.stop_event.set()
        self.tts.stop()

    # ------------------------------------------------------------------
    async def run(self) -> None:
        await self._connect_mcp()
        self.on_log("System", f"Engines — tts: {self.tts.engine_name}, "
                              f"stt: {self.stt.engine_name}, "
                              f"wake: {self.wake.engine_name}")
        await self._say(f"{self.config.assistant_name} online. "
                        "Say my name when you need me.")

        listen_immediately = False
        while not self.stop_event.is_set():
            if not listen_immediately:
                self.on_status("IDLE")
                woke = await asyncio.to_thread(
                    self.wake.wait_for_wake, self.stop_event)
                if not woke or self.stop_event.is_set():
                    break
                await self._say("Yes?")
            listen_immediately = False

            self.on_status("LISTENING")
            text = await asyncio.to_thread(self.stt.listen)
            if self.stop_event.is_set():
                break
            if not text:
                continue
            self.on_log("User", text)

            if self._is_quit(text):
                await self._say("Shutting down. Have a good day.")
                break

            self.on_status("PROCESSING")
            listen_immediately = await self._respond_with_bargein(text)

        self.on_status("OFFLINE")

    # ------------------------------------------------------------------
    async def _respond_with_bargein(self, text: str) -> bool:
        """Stream the reply, speaking sentence by sentence.

        Returns True if the user barged in (caller should listen again
        immediately without waiting for the wake word).
        """
        interrupt = threading.Event()
        wake_task = asyncio.create_task(
            asyncio.to_thread(self.wake.wait_for_wake, interrupt))
        interrupted = False
        try:
            async for sentence in self.brain.respond_stream(text):
                self.on_log(self.config.assistant_name, sentence)
                speak_task = asyncio.create_task(self.tts.speak(sentence))
                done, _ = await asyncio.wait(
                    {speak_task, wake_task},
                    return_when=asyncio.FIRST_COMPLETED)
                if wake_task in done and not wake_task.cancelled() and wake_task.result():
                    self.tts.stop()
                    speak_task.cancel()
                    self.on_log("System", "(interrupted)")
                    interrupted = True
                    break
                await speak_task
        except Exception as e:
            await self._say(f"Something went wrong: {e}")
        finally:
            interrupt.set()
            wake_task.cancel()
            try:
                await wake_task
            except (asyncio.CancelledError, Exception):
                pass
        return interrupted

    async def _say(self, text: str) -> None:
        self.on_log(self.config.assistant_name, text)
        try:
            await self.tts.speak(text)
        except Exception as e:
            self.on_log("System", f"TTS error: {e}")

    def _is_quit(self, text: str) -> bool:
        q = text.lower()
        return any(phrase in q for phrase in (
            f"{self.config.wake_word} quit", "shut down", "shutdown",
            "goodbye", "go to sleep"))

    async def _connect_mcp(self) -> None:
        from pathlib import Path

        if not Path(self.config.mcp_config_path).exists():
            return
        try:
            from jarvis.mcp_client import connect_all

            count = await connect_all(self.config.mcp_config_path)
            if count:
                self.on_log("System", f"MCP: registered {count} external tool(s).")
        except ImportError:
            self.on_log("System", "MCP config found but the 'mcp' package "
                                  "isn't installed (pip install mcp).")
        except Exception as e:
            self.on_log("System", f"MCP connection failed: {e}")
