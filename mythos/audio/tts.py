"""Text-to-speech with barge-in support.

Preferred engine is edge-tts (natural neural voices, free). The generated
audio is played through an external player subprocess (ffplay/mpv/afplay/
PowerShell), which makes speech interruptible: stop() kills the player.
Falls back to pyttsx3 when edge-tts or a player isn't available.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import tempfile
from pathlib import Path

from mythos.config import Config


def _find_player() -> list[str] | None:
    """Locate a CLI audio player able to play an mp3 file (path appended)."""
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet"]
    if platform.system() == "Darwin" and shutil.which("afplay"):
        return ["afplay"]
    if platform.system() == "Windows":
        return ["powershell", "-NoProfile", "-Command",
                "(New-Object Media.SoundPlayer $args[0]).PlaySync()"]
    return None


class TTS:
    def __init__(self, config: Config):
        self.config = config
        self._proc: asyncio.subprocess.Process | None = None
        self._pyttsx3_engine = None
        self._engine = self._pick_engine()

    def _pick_engine(self) -> str:
        want = self.config.tts_engine
        if want in ("auto", "edge"):
            try:
                import edge_tts  # noqa: F401
                if _find_player():
                    return "edge"
            except ImportError:
                pass
            if want == "edge":
                print("[TTS] edge-tts or an audio player is missing; using pyttsx3.")
        return "pyttsx3"

    @property
    def engine_name(self) -> str:
        return self._engine

    # ------------------------------------------------------------------
    async def speak(self, text: str) -> None:
        """Speak text. Cancellable via stop() when using the edge engine."""
        text = text.strip()
        if not text:
            return
        if self._engine == "edge":
            await self._speak_edge(text)
        else:
            await asyncio.to_thread(self._speak_pyttsx3, text)

    def stop(self) -> None:
        """Interrupt current speech (barge-in)."""
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass

    # ------------------------------------------------------------------
    async def _speak_edge(self, text: str) -> None:
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = Path(f.name)
        try:
            communicate = edge_tts.Communicate(text, self.config.tts_voice)
            await communicate.save(str(path))
            player = _find_player()
            if player is None:
                await asyncio.to_thread(self._speak_pyttsx3, text)
                return
            self._proc = await asyncio.create_subprocess_exec(
                *player, str(path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await self._proc.wait()
        finally:
            self._proc = None
            path.unlink(missing_ok=True)

    def _speak_pyttsx3(self, text: str) -> None:
        if self._pyttsx3_engine is None:
            import pyttsx3

            self._pyttsx3_engine = pyttsx3.init()
            voices = self._pyttsx3_engine.getProperty("voices")
            if voices:
                self._pyttsx3_engine.setProperty("voice", voices[0].id)
        self._pyttsx3_engine.say(text)
        self._pyttsx3_engine.runAndWait()
