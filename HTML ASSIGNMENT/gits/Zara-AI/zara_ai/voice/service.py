"""Push-to-talk conversation orchestration."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum

from zara_ai.voice.interfaces import (
    AudioPlayer,
    AudioRecorder,
    ConversationStreamer,
    SpeechRecognizer,
    SpeechSynthesizer,
    StateCallback,
    TextCallback,
    VoiceDeviceError,
)

logger = logging.getLogger(__name__)

VOICE_RESPONSE_INSTRUCTION = (
    "This is a voice conversation and the selected speech voice supports Hindi, "
    "not Romanized Hindi or general Hinglish. Keep Zara's normal identity, "
    "friendly tone, and helpfulness, but write this reply in natural Hindi using "
    "Devanagari script so it can be spoken clearly. Translate ordinary English "
    "phrasing into natural Hindi; retain a technical term or proper name in "
    "Latin script only when necessary. Do not introduce yourself unless asked."
)

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?।])\s+")
_DEVANAGARI = re.compile(r"[\u0900-\u097f]")


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class VoiceTurn:
    transcript: str
    response: str


class VoiceSession:
    """Run one explicitly started microphone turn without saving it as memory."""

    def __init__(
        self,
        engine: ConversationStreamer,
        recorder: AudioRecorder,
        recognizer: SpeechRecognizer,
        synthesizer: SpeechSynthesizer,
        player: AudioPlayer,
        *,
        max_segment_characters: int = 80,
        on_state: StateCallback | None = None,
        on_transcript: TextCallback | None = None,
        on_response_chunk: TextCallback | None = None,
        on_notice: TextCallback | None = None,
    ) -> None:
        if max_segment_characters < 1:
            raise ValueError("max_segment_characters must be positive.")
        self._engine = engine
        self._recorder = recorder
        self._recognizer = recognizer
        self._synthesizer = synthesizer
        self._player = player
        self._max_segment_characters = max_segment_characters
        self._on_state = on_state or (lambda _state: None)
        self._on_transcript = on_transcript or (lambda _text: None)
        self._on_response_chunk = on_response_chunk or (lambda _text: None)
        self._on_notice = on_notice or (lambda _notice: None)
        self._active_task: asyncio.Task[object] | None = None
        self._state = VoiceState.IDLE

    @property
    def state(self) -> VoiceState:
        return self._state

    async def run_turn(self) -> VoiceTurn | None:
        """Capture and process one push-to-talk turn."""
        if self._active_task is not None and not self._active_task.done():
            raise RuntimeError("A voice turn is already active.")
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("Voice processing requires an asyncio task.")

        self._active_task = task
        completed = False
        try:
            self._set_state(VoiceState.LISTENING)
            audio = self._recorder.record()
            self._set_state(VoiceState.TRANSCRIBING)
            transcript = (
                await asyncio.to_thread(self._recognizer.transcribe, audio)
            ).strip()
            if not transcript:
                self._on_notice("No speech was recognized; nothing was sent to Zara.")
                self._set_state(VoiceState.IDLE)
                completed = True
                return None

            self._on_transcript(transcript)
            self._set_state(VoiceState.THINKING)
            response_parts: list[str] = []
            pending_text = ""
            async for chunk in self._engine.stream(
                transcript, system_instruction=VOICE_RESPONSE_INSTRUCTION
            ):
                response_parts.append(chunk)
                pending_text += chunk
                self._on_response_chunk(chunk)
                sentences, pending_text = _split_complete_sentences(pending_text)
                for sentence in sentences:
                    await self._speak(sentence)

            if pending_text.strip():
                for segment in _split_long_text(
                    pending_text.strip(), self._max_segment_characters
                ):
                    await self._speak(segment)

            completed = True
            self._set_state(VoiceState.IDLE)
            return VoiceTurn(transcript, "".join(response_parts))
        except (asyncio.CancelledError, KeyboardInterrupt):
            self._stop_active_audio()
            self._recognizer.cancel()
            self._set_state(VoiceState.INTERRUPTED)
            raise
        finally:
            self._active_task = None
            if not completed and self._state is not VoiceState.INTERRUPTED:
                self._set_state(VoiceState.ERROR)

    def interrupt(self) -> bool:
        """Stop recognition, model generation, or speech playback if active."""
        task = self._active_task
        if task is None or task.done():
            return False
        self._stop_active_audio()
        self._recognizer.cancel()
        if not self._engine.interrupt():
            task.cancel()
        return True

    async def _speak(self, text: str) -> None:
        if not _DEVANAGARI.search(text):
            self._on_notice(
                "This Hindi voice needs Devanagari text; this reply segment "
                "was shown but not spoken."
            )
            return
        self._set_state(VoiceState.SPEAKING)
        audio = await asyncio.to_thread(self._synthesizer.synthesize, text)
        await asyncio.to_thread(self._player.play, audio)
        self._set_state(VoiceState.THINKING)

    def _stop_active_audio(self) -> None:
        try:
            self._player.stop()
        except VoiceDeviceError:
            logger.exception("Could not stop voice playback during interruption.")

    def _set_state(self, state: VoiceState) -> None:
        self._state = state
        self._on_state(state.value)


def _split_complete_sentences(text: str) -> tuple[list[str], str]:
    parts = _SENTENCE_BOUNDARY.split(text)
    if len(parts) == 1:
        return [], text
    return [part.strip() for part in parts[:-1] if part.strip()], parts[-1]


def _split_long_text(text: str, max_characters: int) -> list[str]:
    words = text.split()
    segments: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_characters:
            segments.append(current)
            current = word
        else:
            current = candidate
    if current:
        segments.append(current)
    return segments
