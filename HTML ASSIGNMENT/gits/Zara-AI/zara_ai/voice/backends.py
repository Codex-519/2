"""Local microphone, Qwen ASR, Pocket TTS, and speaker adapters."""

from __future__ import annotations

import json
import logging
import math
import os
import struct
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path
from types import ModuleType
from typing import Any

from zara_ai.config import VoiceConfig
from zara_ai.voice.interfaces import (
    AudioClip,
    VoiceDeviceError,
    VoiceRecognitionError,
    VoiceSetupError,
    VoiceSynthesisError,
)

logger = logging.getLogger(__name__)
_ASR_MODEL_NAME = "Qwen3-ASR-0.6B-Q4_K.gguf"


class MicrophoneRecorder:
    """Open a microphone only for one explicitly started recording."""

    def __init__(
        self,
        max_record_seconds: int,
        *,
        input_func=input,
        output=print,
    ) -> None:
        self._max_record_seconds = max_record_seconds
        self._input = input_func
        self._output = output

    def record(self) -> AudioClip:
        sounddevice = _load_sounddevice()
        self._output(
            "Voice recording is local and push-to-talk. "
            "Press Enter to begin recording."
        )
        self._input()
        frames: list[bytes] = []
        started_at = time.monotonic()

        def capture(indata: bytes, _frames: int, _time: Any, status: Any) -> None:
            if status:
                logger.warning("Audio input status reported: %s", status)
            if time.monotonic() - started_at >= self._max_record_seconds:
                raise sounddevice.CallbackStop
            frames.append(bytes(indata))

        self._output("Recording. Press Enter to stop; Ctrl+C cancels.")
        try:
            with sounddevice.RawInputStream(
                samplerate=16_000,
                channels=1,
                dtype="int16",
                callback=capture,
            ):
                self._input()
        except KeyboardInterrupt:
            raise
        except sounddevice.PortAudioError as error:
            raise VoiceDeviceError(
                "Could not open the microphone. Check Windows microphone privacy "
                "permissions, the selected input device, and that no other app "
                "is holding it."
            ) from error

        samples = b"".join(frames)
        if not samples:
            raise VoiceRecognitionError(
                "No microphone audio was captured. Check the input device and "
                "Windows microphone permissions, then try again."
            )
        if time.monotonic() - started_at >= self._max_record_seconds:
            self._output(
                f"Recording reached the {self._max_record_seconds}-second limit."
            )
        return AudioClip(samples, 16_000, "int16")


class SpeechCppRecognizer:
    """Run the local speech.cpp Vulkan executable on a temporary WAV file."""

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._process_lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    def transcribe(self, audio: AudioClip) -> str:
        if audio.sample_format != "int16" or audio.channels != 1:
            raise VoiceRecognitionError(
                "The local ASR adapter requires mono 16-bit PCM audio."
            )
        executable = self._speech_executable()
        model_path = self._config.data_directory / "asr" / _ASR_MODEL_NAME
        if not model_path.is_file():
            raise VoiceSetupError(
                f"ASR model not found at {model_path}. Run "
                "'python -m zara_ai --setup-voice' first."
            )

        try:
            with tempfile.TemporaryDirectory(prefix="zara-voice-") as directory:
                wav_path = Path(directory) / "input.wav"
                _write_pcm_wav(wav_path, audio)
                environment = os.environ.copy()
                environment["SPEECH_NO_UPDATE_CHECK"] = "1"
                process = subprocess.Popen(
                    [
                        str(executable),
                        "asr",
                        str(model_path),
                        "--format",
                        "json",
                        str(wav_path),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=environment,
                )
                with self._process_lock:
                    self._process = process
                try:
                    stdout, _stderr = process.communicate(timeout=120)
                except subprocess.TimeoutExpired as error:
                    process.terminate()
                    process.communicate()
                    raise VoiceRecognitionError(
                        "Local speech recognition exceeded its 120-second limit."
                    ) from error
                finally:
                    with self._process_lock:
                        self._process = None

                if process.returncode != 0:
                    logger.error(
                        "speech.cpp ASR exited with code %s.", process.returncode
                    )
                    raise VoiceRecognitionError(
                        "Local speech recognition failed. Check the ASR model, "
                        "Vulkan runtime, and Zara AI log."
                    )
                return _read_asr_text(stdout)
        except VoiceRecognitionError:
            raise
        except OSError as error:
            raise VoiceRecognitionError(
                "Could not start the local speech.cpp recognizer. Verify its "
                "runtime files and Windows Vulkan driver."
            ) from error

    def cancel(self) -> None:
        with self._process_lock:
            process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                logger.warning("ASR process had already stopped during cancellation.")

    def _speech_executable(self) -> Path:
        runtime_directory = self._config.data_directory / "runtime"
        executable = runtime_directory / "speech.exe"
        if executable.is_file():
            return executable
        if runtime_directory.is_dir():
            matches = tuple(runtime_directory.rglob("speech.exe"))
            if len(matches) == 1:
                return matches[0]
        raise VoiceSetupError(
            f"speech.cpp runtime not found under {runtime_directory}. Run "
            "'python -m zara_ai --setup-voice' first."
        )


class PocketHindiSynthesizer:
    """Load the installed Hindi Pocket TTS model lazily and speak text."""

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._model: Any = None
        self._voice_state: Any = None

    def synthesize(self, text: str) -> AudioClip:
        if not text.strip():
            raise ValueError("Speech text must not be empty.")
        try:
            import numpy
            from pocket_tts import TTSModel
        except (ImportError, OSError) as error:
            raise VoiceSetupError(
                'Install the optional voice dependencies with '
                '`python -m pip install -e ".[voice]"`.'
            ) from error

        config_path = self._config.data_directory / "tts" / "config.local.yaml"
        reference_path = self._config.reference_wav
        weights_path = (
            self._config.data_directory / "tts" / "model_bf16.safetensors"
        )
        if not config_path.is_file() or not weights_path.is_file():
            raise VoiceSetupError(
                f"Hindi TTS model is missing under {self._config.data_directory}. "
                "Run 'python -m zara_ai --setup-voice' first."
            )
        if not reference_path.is_file():
            raise VoiceSetupError(
                f"Voice reference WAV not found at {reference_path}. "
                "Set voice.reference_wav to an existing WAV file."
            )

        try:
            if self._model is None:
                model = TTSModel.load_model(config=str(config_path))
                voice_state = model.get_state_for_audio_prompt(
                    str(reference_path)
                )
                self._model = model
                self._voice_state = voice_state
            generated = self._model.generate_audio(self._voice_state, text)
            samples = numpy.asarray(
                generated.detach().cpu().numpy(), dtype=numpy.float32
            ).reshape(-1)
            if samples.size == 0:
                raise VoiceSynthesisError("Hindi TTS returned no audio samples.")
            return AudioClip(
                _normalize_float32_samples(
                    samples.astype("<f4", copy=False).tobytes()
                ),
                int(self._model.sample_rate),
                "float32",
            )
        except VoiceSynthesisError:
            raise
        except (OSError, RuntimeError, ValueError) as error:
            raise VoiceSynthesisError(
                "The local Hindi speech model could not synthesize this text."
            ) from error


def _normalize_float32_samples(samples: bytes) -> bytes:
    if not samples or len(samples) % 4:
        raise VoiceSynthesisError("Hindi TTS returned an invalid audio buffer.")
    values = tuple(value for (value,) in struct.iter_unpack("<f", samples))
    if any(not math.isfinite(value) for value in values):
        raise VoiceSynthesisError("Hindi TTS returned non-finite audio samples.")
    peak = max(abs(value) for value in values)
    if peak == 0:
        raise VoiceSynthesisError("Hindi TTS returned silent audio.")

    gain = 0.8 / peak
    normalized = bytearray(len(samples))
    for index, value in enumerate(values):
        struct.pack_into("<f", normalized, index * 4, value * gain)
    return bytes(normalized)


class SoundDevicePlayer:
    """Play local float audio and allow the active output stream to be stopped."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stream: Any = None
        self._stop_event: threading.Event | None = None

    def play(self, audio: AudioClip) -> None:
        if audio.sample_format != "float32" or audio.channels != 1:
            raise VoiceDeviceError(
                "The local speaker adapter requires mono float32 audio."
            )
        sounddevice = _load_sounddevice()
        stop_event = threading.Event()
        stream: Any = None
        try:
            stream = sounddevice.RawOutputStream(
                samplerate=audio.sample_rate,
                channels=1,
                dtype="float32",
            )
            with self._lock:
                if self._stream is not None:
                    raise VoiceDeviceError("Audio playback is already active.")
                self._stream = stream
                self._stop_event = stop_event
            stream.start()
            bytes_per_frame = 4 * audio.channels
            frames_per_write = max(1, audio.sample_rate // 20)
            bytes_per_write = frames_per_write * bytes_per_frame
            for offset in range(0, len(audio.samples), bytes_per_write):
                if stop_event.is_set():
                    break
                try:
                    stream.write(audio.samples[offset : offset + bytes_per_write])
                except sounddevice.PortAudioError as error:
                    if stop_event.is_set():
                        break
                    raise VoiceDeviceError(
                        "Could not play audio. Check the Windows output device "
                        "and speaker permissions."
                    ) from error
        except sounddevice.PortAudioError as error:
            raise VoiceDeviceError(
                "Could not play audio. Check the Windows output device and "
                "speaker permissions."
            ) from error
        finally:
            with self._lock:
                active_stream = stream
                if self._stream is active_stream:
                    self._stream = None
                    self._stop_event = None
            if active_stream is not None:
                try:
                    active_stream.close()
                except sounddevice.PortAudioError as error:
                    raise VoiceDeviceError(
                        "Could not close the audio output stream cleanly."
                    ) from error

    def stop(self) -> None:
        sounddevice = _load_sounddevice()
        with self._lock:
            stream = self._stream
            stop_event = self._stop_event
            if stream is None or stop_event is None or stop_event.is_set():
                return
            stop_event.set()
            try:
                stream.abort()
            except sounddevice.PortAudioError as error:
                raise VoiceDeviceError(
                    "Could not stop the active speaker stream."
                ) from error


def _load_sounddevice() -> ModuleType:
    try:
        import sounddevice
    except (ImportError, OSError) as error:
        raise VoiceSetupError(
            'Install the optional voice dependencies with '
            '`python -m pip install -e ".[voice]"`.'
        ) from error
    return sounddevice


def _write_pcm_wav(path: Path, audio: AudioClip) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(audio.channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(audio.sample_rate)
        wav_file.writeframes(audio.samples)


def _read_asr_text(output: str) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        raise VoiceRecognitionError(
            "The local recognizer returned no transcription."
        )
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as error:
        raise VoiceRecognitionError(
            "The local recognizer returned invalid JSON output."
        ) from error
    if not isinstance(result, dict) or not isinstance(result.get("text"), str):
        raise VoiceRecognitionError(
            "The local recognizer returned an unexpected result."
        )
    return result["text"]
