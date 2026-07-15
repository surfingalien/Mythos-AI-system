"""Speech-to-text.

Preferred engine is faster-whisper running locally (accurate, offline).
Falls back to the Google Web Speech API via speech_recognition. Microphone
capture uses speech_recognition's energy-based endpointing in both cases.
"""

from __future__ import annotations

from jarvis.config import Config


class STT:
    def __init__(self, config: Config):
        self.config = config
        self._whisper = None
        self._engine = self._pick_engine()

    def _pick_engine(self) -> str:
        want = self.config.stt_engine
        if want in ("auto", "whisper"):
            try:
                import faster_whisper  # noqa: F401
                return "whisper"
            except ImportError:
                if want == "whisper":
                    print("[STT] faster-whisper not installed; using Google Web Speech.")
        return "google"

    @property
    def engine_name(self) -> str:
        return self._engine

    # ------------------------------------------------------------------
    def listen(self, phrase_time_limit: float | None = 15,
               timeout: float | None = 8) -> str:
        """Record one utterance from the microphone and transcribe it.

        Returns "" when nothing intelligible was heard. Blocking — run in a
        thread from async code.
        """
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 0.8
        with sr.Microphone(sample_rate=16000) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            try:
                audio = recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return ""
        return self.transcribe(audio, recognizer)

    def transcribe(self, audio, recognizer=None) -> str:
        """Transcribe a speech_recognition AudioData object."""
        if self._engine == "whisper":
            return self._transcribe_whisper(audio)
        return self._transcribe_google(audio, recognizer)

    # ------------------------------------------------------------------
    def _transcribe_whisper(self, audio) -> str:
        import numpy as np

        if self._whisper is None:
            from faster_whisper import WhisperModel

            self._whisper = WhisperModel(
                self.config.whisper_model, device="cpu", compute_type="int8")

        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._whisper.transcribe(
            samples, language="en", vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip().lower()

    def _transcribe_google(self, audio, recognizer=None) -> str:
        import speech_recognition as sr

        recognizer = recognizer or sr.Recognizer()
        try:
            return recognizer.recognize_google(audio, language="en-in").lower()
        except (sr.UnknownValueError, sr.RequestError):
            return ""
