"""Wake-word detection.

Preferred engine is openWakeWord, which ships a pretrained "hey jarvis"
model and runs fully offline with low latency. Falls back to a
speech_recognition keyword loop (online, slower) when unavailable.
"""

from __future__ import annotations

import threading

from jarvis.config import Config

_FRAME_SAMPLES = 1280  # 80 ms at 16 kHz, openWakeWord's expected chunk


class WakeWordDetector:
    def __init__(self, config: Config, stt=None):
        self.config = config
        self._stt = stt  # reused for the fallback keyword loop
        self._oww_model = None
        self._engine = self._pick_engine()

    def _pick_engine(self) -> str:
        want = self.config.wake_engine
        if want in ("auto", "openwakeword"):
            try:
                import openwakeword  # noqa: F401
                import pyaudio  # noqa: F401
                return "openwakeword"
            except ImportError:
                if want == "openwakeword":
                    print("[Wake] openwakeword/pyaudio not installed; "
                          "using speech-recognition fallback.")
        return "google"

    @property
    def engine_name(self) -> str:
        return self._engine

    # ------------------------------------------------------------------
    def wait_for_wake(self, stop_event: threading.Event) -> bool:
        """Block until the wake word is heard or stop_event is set.

        Returns True on wake, False on stop. Blocking — run in a thread
        from async code.
        """
        if self._engine == "openwakeword":
            return self._wait_openwakeword(stop_event)
        return self._wait_google(stop_event)

    # ------------------------------------------------------------------
    def _wait_openwakeword(self, stop_event: threading.Event) -> bool:
        import numpy as np
        import pyaudio
        from openwakeword.model import Model

        if self._oww_model is None:
            # "hey_jarvis" is one of openWakeWord's bundled pretrained models.
            self._oww_model = Model(wakeword_models=["hey_jarvis"])
        model = self._oww_model
        model.reset()

        pa = pyaudio.PyAudio()
        stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16,
                         input=True, frames_per_buffer=_FRAME_SAMPLES)
        try:
            while not stop_event.is_set():
                frame = np.frombuffer(
                    stream.read(_FRAME_SAMPLES, exception_on_overflow=False),
                    dtype=np.int16)
                prediction = model.predict(frame)
                if any(score >= self.config.wake_threshold
                       for score in prediction.values()):
                    return True
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
        return False

    def _wait_google(self, stop_event: threading.Event) -> bool:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            while not stop_event.is_set():
                try:
                    audio = recognizer.listen(
                        source, timeout=3, phrase_time_limit=3)
                except sr.WaitTimeoutError:
                    continue
                try:
                    text = recognizer.recognize_google(
                        audio, language="en-in").lower()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    stop_event.wait(2.0)  # avoid a busy loop when offline
                    continue
                if self.config.wake_word in text:
                    return True
        return False
