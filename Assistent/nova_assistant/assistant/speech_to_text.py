"""Microphone capture with Google Speech Recognition and optional Vosk."""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
import speech_recognition as sr


class SpeechRecognitionError(RuntimeError):
    """A recoverable microphone or speech recognition error."""


class SpeechToText:
    def __init__(
        self,
        provider: str = "google",
        language: str = "en-IN",
        listen_seconds: int = 5,
        vosk_model_path: str = "",
    ) -> None:
        self.provider = provider.lower()
        self.language = language
        self.listen_seconds = max(2, listen_seconds)
        self.vosk_model_path = vosk_model_path
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self._vosk_model = None
        self._vosk_error: str | None = None

    def _record(self, seconds: int | None = None) -> sr.AudioData:
        duration = seconds or self.listen_seconds
        try:
            sample_rate = 16_000
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()
            return sr.AudioData(audio.tobytes(), sample_rate, 2)
        except Exception as exc:
            raise SpeechRecognitionError(
                "Microphone unavailable. Check Windows microphone permissions "
                "and select a working input device."
            ) from exc

    def transcribe(self, seconds: int | None = None) -> str:
        audio = self._record(seconds)
        if self.provider == "vosk":
            return self._transcribe_vosk(audio)
        return self._transcribe_google(audio)

    def _transcribe_google(self, audio: sr.AudioData) -> str:
        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
            return text.strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            raise SpeechRecognitionError(
                "Speech recognition needs an internet connection. "
                "You can switch STT_PROVIDER to vosk for offline recognition."
            ) from exc

    def _load_vosk(self):
        if self._vosk_model is not None:
            return self._vosk_model
        if not self.vosk_model_path:
            raise SpeechRecognitionError(
                "Vosk is selected, but VOSK_MODEL_PATH is empty. "
                "Download a Vosk model and set its folder in .env."
            )
        try:
            from vosk import Model

            model_path = Path(self.vosk_model_path).expanduser()
            if not model_path.exists():
                raise FileNotFoundError(model_path)
            self._vosk_model = Model(str(model_path))
            return self._vosk_model
        except ImportError as exc:
            raise SpeechRecognitionError(
                "The optional vosk package is not installed. "
                "Run: python -m pip install vosk"
            ) from exc
        except OSError as exc:
            raise SpeechRecognitionError("The configured Vosk model folder is invalid.") from exc

    def _transcribe_vosk(self, audio: sr.AudioData) -> str:
        try:
            from vosk import KaldiRecognizer

            recognizer = KaldiRecognizer(self._load_vosk(), audio.sample_rate)
            recognizer.AcceptWaveform(audio.get_raw_data())
            result = json.loads(recognizer.FinalResult())
            return str(result.get("text", "")).strip()
        except SpeechRecognitionError:
            raise
        except Exception as exc:
            raise SpeechRecognitionError("Offline speech recognition failed.") from exc

    def listen_loop(
        self,
        stop_event: threading.Event,
        wake_word: str,
        start_armed: bool,
        on_wake: Callable[[], None],
        on_command: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Continuously sample short chunks and dispatch wake words/commands."""
        armed = start_armed
        wake = wake_word.lower().strip()
        while not stop_event.is_set():
            try:
                text = self.transcribe(seconds=3)
                if not text:
                    continue
                lowered = text.lower()
                if armed:
                    if wake in lowered:
                        armed = False
                        remainder = lowered.split(wake, 1)[1].strip(" ,.!?")
                        on_wake()
                        if remainder:
                            on_command(remainder)
                            armed = True
                else:
                    on_command(text)
                    armed = True
            except SpeechRecognitionError as exc:
                on_error(str(exc))
                stop_event.wait(2)


class MicrophoneWorker:
    """Owns the daemon thread used by the UI for wake-word listening."""

    def __init__(self, stt: SpeechToText) -> None:
        self.stt = stt
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self, start_armed: bool = True, **callbacks) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self.stt.listen_loop,
            kwargs={
                "stop_event": self.stop_event,
                "wake_word": callbacks.pop("wake_word", "hey nova"),
                "start_armed": start_armed,
                **callbacks,
            },
            daemon=True,
            name="nova-microphone",
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)