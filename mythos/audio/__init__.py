"""Audio subsystem: text-to-speech, speech-to-text, and wake-word detection.

Every engine has a modern default and a legacy fallback, chosen at runtime
based on which optional packages are installed:

  TTS:  edge-tts (neural voices)  ->  pyttsx3
  STT:  faster-whisper (local)    ->  Google Web Speech (speech_recognition)
  Wake: openWakeWord (offline)    ->  Google Web Speech keyword loop
"""
