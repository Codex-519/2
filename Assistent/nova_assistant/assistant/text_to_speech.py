"""Replaceable text-to-speech service using Windows SAPI through pyttsx3."""

from __future__ import annotations

import threading
from typing import Any


class TextToSpeechError(RuntimeError):
    """A recoverable speech synthesis error."""


class TextToSpeech:
    def __init__(self, engine_name: str, voice_name: str, rate: int, volume: float) -> None:
        self.engine_name = engine_name
        self.voice_name = voice_name.strip()
        self.rate = rate
        self.volume = max(0.0, min(volume, 1.0))
        self._lock = threading.Lock()

    def available_voices(self) -> list[dict[str, str]]:
        try:
            import pyttsx3

            engine = pyttsx3.init(None if self.engine_name in {"", "pyttsx3"} else self.engine_name)
            voices = [
                {
                    "id": str(getattr(voice, "id", "")),
                    "name": str(getattr(voice, "name", "")),
                    "languages": str(getattr(voice, "languages", "")),
                }
                for voice in engine.getProperty("voices")
            ]
            engine.stop()
            return voices
        except Exception as exc:
            raise TextToSpeechError(
                "Windows text-to-speech is unavailable. Check that SAPI voices are installed."
            ) from exc

    def _choose_voice(self, engine: Any) -> None:
        voices = engine.getProperty("voices") or []
        if self.voice_name:
            wanted = self.voice_name.lower()
            for voice in voices:
                identity = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
                if wanted in identity:
                    engine.setProperty("voice", voice.id)
                    return
        # Prefer voices whose Windows metadata suggests a feminine voice.
        for voice in voices:
            identity = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
            if any(term in identity for term in ("female", "zira", "samantha", "hazel", "heera")):
                engine.setProperty("voice", voice.id)
                return
        if voices:
            engine.setProperty("voice", voices[0].id)

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        try:
            import pyttsx3

            with self._lock:
                engine = pyttsx3.init(None if self.engine_name in {"", "pyttsx3"} else self.engine_name)
                self._choose_voice(engine)
                engine.setProperty("rate", self.rate)
                engine.setProperty("volume", self.volume)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
        except Exception as exc:
            raise TextToSpeechError(
                "I couldn't play my voice. Check the Windows speaker and SAPI voice settings."
            ) from exc