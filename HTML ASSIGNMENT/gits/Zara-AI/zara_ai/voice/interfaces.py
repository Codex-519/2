"""Backend-neutral audio types and interfaces."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Literal, Protocol


class VoiceError(RuntimeError):
    """Base class for actionable voice subsystem errors."""


class VoiceSetupError(VoiceError):
    """A required optional package, executable, or model is unavailable."""


class VoiceDeviceError(VoiceError):
    """A microphone or speaker could not be opened."""


class VoiceRecognitionError(VoiceError):
    """Local speech recognition failed."""


class VoiceSynthesisError(VoiceError):
    """Local speech synthesis failed."""


@dataclass(frozen=True, slots=True)
class AudioClip:
    samples: bytes
    sample_rate: int
    sample_format: Literal["int16", "float32"]
    channels: int = 1

    def __post_init__(self) -> None:
        if not self.samples:
            raise ValueError("Audio clip must contain samples.")
        if self.sample_rate <= 0 or self.channels <= 0:
            raise ValueError("Audio sample rate and channel count must be positive.")


class AudioRecorder(Protocol):
    def record(self) -> AudioClip: ...


class SpeechRecognizer(Protocol):
    def transcribe(self, audio: AudioClip) -> str: ...

    def cancel(self) -> None: ...


class SpeechSynthesizer(Protocol):
    def synthesize(self, text: str) -> AudioClip: ...


class AudioPlayer(Protocol):
    def play(self, audio: AudioClip) -> None: ...

    def stop(self) -> None: ...


StateCallback = Callable[[str], None]
TextCallback = Callable[[str], None]


class ConversationStreamer(Protocol):
    def stream(
        self, prompt: str, *, system_instruction: str | None = None
    ) -> AsyncIterator[str]: ...

    def interrupt(self) -> bool: ...
