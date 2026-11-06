from __future__ import annotations

import asyncio
import json
import sys
import struct
import threading
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx

from zara_ai.config import AppConfig, GenerationConfig, OllamaConfig, VoiceConfig
from zara_ai.conversation.engine import ConversationEngine
from zara_ai.conversation.ollama import OllamaClient
from zara_ai.memory.store import MemoryStore
from zara_ai.voice.backends import (
    MicrophoneRecorder,
    PocketHindiSynthesizer,
    SoundDevicePlayer,
    _normalize_float32_samples,
    _read_asr_text,
)
from zara_ai.voice.interfaces import (
    AudioClip,
    VoiceDeviceError,
    VoiceRecognitionError,
    VoiceSetupError,
    VoiceSynthesisError,
)
from zara_ai.voice.service import VoiceSession, VoiceState
from zara_ai.voice.setup import _safe_extract, _write_local_tts_config


class _Recorder:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def record(self) -> AudioClip:
        if self.error:
            raise self.error
        return AudioClip(b"\x00\x00" * 64, 16_000, "int16")


class _Recognizer:
    def __init__(self, transcript: str) -> None:
        self.transcript = transcript
        self.cancelled = False

    def transcribe(self, _audio: AudioClip) -> str:
        return self.transcript

    def cancel(self) -> None:
        self.cancelled = True


class _FailingRecognizer(_Recognizer):
    def __init__(self, error: Exception) -> None:
        super().__init__("")
        self.error = error

    def transcribe(self, _audio: AudioClip) -> str:
        raise self.error


class _Synthesizer:
    def __init__(self, error: Exception | None = None) -> None:
        self.texts: list[str] = []
        self.error = error

    def synthesize(self, text: str) -> AudioClip:
        self.texts.append(text)
        if self.error:
            raise self.error
        return AudioClip(b"\x00\x00\x00\x00" * 8, 24_000, "float32")


class _Player:
    def __init__(self) -> None:
        self.played: list[AudioClip] = []
        self.stopped = 0

    def play(self, audio: AudioClip) -> None:
        self.played.append(audio)

    def stop(self) -> None:
        self.stopped += 1


class _FailingPlayer(_Player):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    def play(self, audio: AudioClip) -> None:
        raise self.error


class _FakePortAudioError(Exception):
    pass


class _FakeOutputStream:
    block_writes = False
    instances: list[_FakeOutputStream] = []
    started_event = threading.Event()

    def __init__(self, **_kwargs) -> None:
        self.writes: list[bytes] = []
        self.write_started = threading.Event()
        self.write_released = threading.Event()
        self.aborted = False
        self.abort_count = 0
        self.closed = False
        self.instances.append(self)

    def start(self) -> None:
        pass

    def write(self, data: bytes) -> None:
        self.writes.append(bytes(data))
        self.write_started.set()
        self.started_event.set()
        if self.block_writes:
            self.write_released.wait(timeout=2)
            if self.aborted:
                raise _FakePortAudioError("stream aborted")

    def abort(self) -> None:
        self.abort_count += 1
        self.aborted = True
        self.write_released.set()

    def close(self) -> None:
        self.closed = True


class _FakeSamples:
    def __init__(self, values: tuple[float, ...]) -> None:
        self.values = values
        self.size = len(values)

    def reshape(self, *_shape) -> _FakeSamples:
        return self

    def astype(self, *_args, **_kwargs) -> _FakeSamples:
        return self

    def tobytes(self) -> bytes:
        return struct.pack(f"<{self.size}f", *self.values)


class _FakeTensor:
    def __init__(self, values: tuple[float, ...]) -> None:
        self.values = values

    def detach(self) -> _FakeTensor:
        return self

    def cpu(self) -> _FakeTensor:
        return self

    def numpy(self) -> _FakeSamples:
        return _FakeSamples(self.values)


class _Engine:
    def __init__(self, chunks: tuple[str, ...] = ("नमस्ते।", " मैं Zara हूँ।")) -> None:
        self.chunks = chunks
        self.calls: list[tuple[str, str | None]] = []
        self.active_task: asyncio.Task[object] | None = None
        self.started = asyncio.Event()

    async def stream(self, prompt: str, *, system_instruction: str | None = None):
        self.calls.append((prompt, system_instruction))
        self.active_task = asyncio.current_task()
        for chunk in self.chunks:
            yield chunk
        self.started.set()

    def interrupt(self) -> bool:
        task = self.active_task
        if task is None or task.done():
            return False
        task.cancel()
        return True


class VoiceSessionTests(unittest.IsolatedAsyncioTestCase):
    def _session(
        self,
        *,
        engine=None,
        recorder=None,
        recognizer=None,
        synthesizer=None,
        player=None,
        states=None,
        notices=None,
    ):
        selected_engine = engine or _Engine()
        selected_recorder = recorder or _Recorder()
        selected_recognizer = recognizer or _Recognizer("नमस्ते Zara")
        selected_synthesizer = synthesizer or _Synthesizer()
        selected_player = player or _Player()
        return (
            VoiceSession(
                selected_engine,
                selected_recorder,
                selected_recognizer,
                selected_synthesizer,
                selected_player,
                on_state=states.append if states is not None else None,
                on_notice=notices.append if notices is not None else None,
            ),
            selected_engine,
            selected_recognizer,
            selected_synthesizer,
            selected_player,
        )

    async def test_voice_turn_streams_hindi_and_speaks_in_segments(self) -> None:
        states: list[str] = []
        session, engine, _, synthesizer, player = self._session(states=states)

        turn = await session.run_turn()

        self.assertEqual(turn.transcript, "नमस्ते Zara")
        self.assertEqual(turn.response, "नमस्ते। मैं Zara हूँ।")
        self.assertEqual(engine.calls[0][0], turn.transcript)
        self.assertIn("Devanagari", engine.calls[0][1])
        self.assertEqual(len(synthesizer.texts), 2)
        self.assertEqual(len(player.played), 2)
        self.assertIn(VoiceState.LISTENING.value, states)
        self.assertIn(VoiceState.TRANSCRIBING.value, states)
        self.assertIn(VoiceState.THINKING.value, states)
        self.assertIn(VoiceState.SPEAKING.value, states)
        self.assertEqual(session.state, VoiceState.IDLE)

    async def test_empty_transcript_does_not_send_a_prompt(self) -> None:
        notices: list[str] = []
        session, engine, _, _, _ = self._session(
            recognizer=_Recognizer("  "),
            notices=notices,
        )

        self.assertIsNone(await session.run_turn())
        self.assertEqual(engine.calls, [])
        self.assertIn("nothing was sent", notices[0])
        self.assertEqual(session.state, VoiceState.IDLE)

    async def test_microphone_permission_error_is_reported(self) -> None:
        session, _, _, _, _ = self._session(
            recorder=_Recorder(VoiceDeviceError("microphone denied"))
        )

        with self.assertRaisesRegex(VoiceDeviceError, "microphone denied"):
            await session.run_turn()
        self.assertEqual(session.state, VoiceState.ERROR)

    async def test_tts_failure_sets_error_state_and_is_not_silenced(self) -> None:
        session, _, _, _, _ = self._session(
            synthesizer=_Synthesizer(VoiceSynthesisError("TTS unavailable"))
        )

        with self.assertRaisesRegex(VoiceSynthesisError, "TTS unavailable"):
            await session.run_turn()
        self.assertEqual(session.state, VoiceState.ERROR)

    async def test_asr_failure_is_reported_without_calling_conversation_engine(self) -> None:
        engine = _Engine()
        session, _, recognizer, _, _ = self._session(
            engine=engine,
            recognizer=_FailingRecognizer(
                VoiceRecognitionError("Local ASR failed.")
            ),
        )

        with self.assertRaisesRegex(VoiceRecognitionError, "Local ASR failed"):
            await session.run_turn()

        self.assertEqual(engine.calls, [])
        self.assertEqual(session.state, VoiceState.ERROR)
        self.assertFalse(recognizer.cancelled)

    async def test_playback_failure_is_reported_and_sets_error_state(self) -> None:
        session, engine, _, synthesizer, _ = self._session(
            player=_FailingPlayer(VoiceDeviceError("Speaker unavailable."))
        )

        with self.assertRaisesRegex(VoiceDeviceError, "Speaker unavailable"):
            await session.run_turn()

        self.assertTrue(engine.calls)
        self.assertTrue(synthesizer.texts)
        self.assertEqual(session.state, VoiceState.ERROR)

    async def test_interrupt_stops_playback_and_cancels_stream(self) -> None:
        blocking_engine = _Engine(chunks=("अधूरा जवाब",))

        async def blocking_stream(prompt: str, *, system_instruction=None):
            blocking_engine.calls.append((prompt, system_instruction))
            blocking_engine.active_task = asyncio.current_task()
            yield "अधूरा जवाब"
            blocking_engine.started.set()
            await asyncio.Event().wait()

        blocking_engine.stream = blocking_stream
        session, _, recognizer, _, player = self._session(engine=blocking_engine)
        task = asyncio.create_task(session.run_turn())
        await asyncio.wait_for(blocking_engine.started.wait(), timeout=1)

        self.assertTrue(session.interrupt())
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertGreaterEqual(player.stopped, 1)
        self.assertTrue(recognizer.cancelled)
        self.assertEqual(session.state, VoiceState.INTERRUPTED)
        self.assertFalse(session.interrupt())

    async def test_interrupt_stops_an_active_speaker_stream(self) -> None:
        started = threading.Event()
        stopped = threading.Event()

        class BlockingPlayer(_Player):
            def play(self, audio: AudioClip) -> None:
                self.played.append(audio)
                started.set()
                stopped.wait(timeout=5)

            def stop(self) -> None:
                super().stop()
                stopped.set()

        player = BlockingPlayer()
        session, _, _, _, _ = self._session(
            engine=_Engine(chunks=("नमस्ते।",)),
            player=player,
        )
        task = asyncio.create_task(session.run_turn())
        self.assertTrue(await asyncio.to_thread(started.wait, 1))

        self.assertTrue(session.interrupt())
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertGreaterEqual(player.stopped, 1)
        self.assertEqual(session.state, VoiceState.INTERRUPTED)

    async def test_interrupt_releases_sounddevice_playback_worker(self) -> None:
        _FakeOutputStream.instances.clear()
        _FakeOutputStream.block_writes = True
        _FakeOutputStream.started_event.clear()
        fake_sounddevice = types.ModuleType("sounddevice")
        fake_sounddevice.RawOutputStream = _FakeOutputStream
        fake_sounddevice.PortAudioError = _FakePortAudioError
        player = SoundDevicePlayer()
        session, _, _, _, _ = self._session(
            engine=_Engine(chunks=("नमस्ते।",)),
            player=player,
        )
        with patch.dict(sys.modules, {"sounddevice": fake_sounddevice}):
            task = asyncio.create_task(session.run_turn())
            stream_started = await asyncio.to_thread(
                _FakeOutputStream.started_event.wait, 1
            )
            self.assertTrue(stream_started)
            self.assertTrue(session.interrupt())
            with self.assertRaises(asyncio.CancelledError):
                await task
            stream = _FakeOutputStream.instances[0]
            self.assertTrue(stream.write_released.wait(timeout=1))
            self.assertTrue(stream.aborted)
            self.assertTrue(stream.closed)
        _FakeOutputStream.block_writes = False

    async def test_voice_conversation_is_not_saved_as_long_term_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.sqlite3")
            store.enable()
            requests = []

            def handler(request: httpx.Request) -> httpx.Response:
                requests.append(json.loads(request.content))
                payload = (
                    json.dumps(
                        {"message": {"content": "मैं Zara हूँ।"}, "done": False}
                    )
                    + "\n"
                    + json.dumps({"message": {"content": ""}, "done": True})
                    + "\n"
                )
                return httpx.Response(200, content=payload.encode())

            client = OllamaClient(
                AppConfig(
                    ollama=OllamaConfig(),
                    generation=GenerationConfig(),
                ),
                transport=httpx.MockTransport(handler),
            )
            engine = ConversationEngine(client, store)
            session, _, _, _, _ = self._session(engine=engine)
            try:
                await session.run_turn()
                self.assertEqual(
                    [message.content for message in engine.history],
                    ["नमस्ते Zara", "मैं Zara हूँ।"],
                )
                self.assertEqual(store.list_memories(), ())
                self.assertTrue(store.enabled)
                self.assertIn(
                    "Devanagari",
                    requests[0]["messages"][1]["content"],
                )
            finally:
                await client.aclose()


class VoiceBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeOutputStream.instances.clear()
        _FakeOutputStream.block_writes = False
        _FakeOutputStream.started_event.clear()
        self.fake_sounddevice = types.ModuleType("sounddevice")
        self.fake_sounddevice.RawOutputStream = _FakeOutputStream
        self.fake_sounddevice.PortAudioError = _FakePortAudioError
        self.sounddevice_patch = patch.dict(
            sys.modules, {"sounddevice": self.fake_sounddevice}
        )
        self.sounddevice_patch.start()
        self.addCleanup(self.sounddevice_patch.stop)

    def test_pocket_tts_uses_and_caches_configured_reference_voice(self) -> None:
        class FakeModel:
            sample_rate = 24_000

            def __init__(self) -> None:
                self.prompt_paths: list[str] = []
                self.generated: list[tuple[object, str]] = []

            def get_state_for_audio_prompt(self, prompt_path: str) -> object:
                self.prompt_paths.append(prompt_path)
                return object()

            def generate_audio(
                self, state: object, text: str
            ) -> _FakeTensor:
                self.generated.append((state, text))
                return _FakeTensor((0.1, -0.2, 0.3))

        model = FakeModel()
        load_calls: list[str] = []

        class FakeTTSModel:
            @staticmethod
            def load_model(*, config: str) -> FakeModel:
                load_calls.append(config)
                return model

        fake_numpy = types.ModuleType("numpy")
        fake_numpy.float32 = "float32"
        fake_numpy.asarray = lambda samples, dtype: samples
        fake_pocket_tts = types.ModuleType("pocket_tts")
        fake_pocket_tts.TTSModel = FakeTTSModel

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_directory = root / "voice-data"
            tts_directory = data_directory / "tts"
            tts_directory.mkdir(parents=True)
            config_path = tts_directory / "config.local.yaml"
            config_path.touch()
            (tts_directory / "model_bf16.safetensors").touch()
            reference_path = root / "reference.wav"
            reference_path.touch()
            synthesizer = PocketHindiSynthesizer(
                VoiceConfig(
                    data_directory=data_directory,
                    reference_wav=reference_path,
                )
            )

            with patch.dict(
                sys.modules,
                {"numpy": fake_numpy, "pocket_tts": fake_pocket_tts},
            ):
                first_clip = synthesizer.synthesize("नमस्ते")
                second_clip = synthesizer.synthesize("कैसे हो?")

        self.assertEqual(len(load_calls), 1)
        self.assertEqual(
            model.prompt_paths,
            [str(reference_path)],
        )
        self.assertEqual(
            [text for _, text in model.generated],
            ["नमस्ते", "कैसे हो?"],
        )
        self.assertIs(model.generated[0][0], model.generated[1][0])
        self.assertEqual(first_clip.sample_rate, 24_000)
        self.assertEqual(second_clip.sample_format, "float32")

    def test_pocket_tts_reports_missing_reference_wav(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tts_directory = root / "voice-data" / "tts"
            tts_directory.mkdir(parents=True)
            (tts_directory / "config.local.yaml").touch()
            (tts_directory / "model_bf16.safetensors").touch()
            reference_path = root / "missing-reference.wav"
            synthesizer = PocketHindiSynthesizer(
                VoiceConfig(
                    data_directory=root / "voice-data",
                    reference_wav=reference_path,
                )
            )

            with self.assertRaises(VoiceSetupError) as raised:
                synthesizer.synthesize("नमस्ते")
            self.assertIn(
                f"Voice reference WAV not found at {reference_path}",
                str(raised.exception),
            )

    def test_sounddevice_player_completes_normal_playback_in_chunks(self) -> None:
        audio = AudioClip(b"\x00" * (24_000 * 4), 24_000, "float32")

        SoundDevicePlayer().play(audio)

        stream = _FakeOutputStream.instances[0]
        self.assertEqual(b"".join(stream.writes), audio.samples)
        self.assertGreater(len(stream.writes), 1)
        self.assertLessEqual(max(map(len, stream.writes)), 24_000 // 20 * 4)
        self.assertTrue(stream.closed)
        self.assertEqual(stream.abort_count, 0)

    def test_sounddevice_player_stop_releases_blocked_playback(self) -> None:
        _FakeOutputStream.block_writes = True
        audio = AudioClip(b"\x00" * (24_000 * 4), 24_000, "float32")
        player = SoundDevicePlayer()
        errors: list[BaseException] = []

        def play() -> None:
            try:
                player.play(audio)
            except BaseException as error:
                errors.append(error)

        worker = threading.Thread(target=play)
        worker.start()
        stream = _FakeOutputStream.instances[0]
        self.assertTrue(stream.write_started.wait(timeout=1))

        player.stop()
        worker.join(timeout=1)

        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(stream.aborted)
        self.assertTrue(stream.closed)

    def test_sounddevice_player_repeated_stop_is_idempotent(self) -> None:
        _FakeOutputStream.block_writes = True
        audio = AudioClip(b"\x00" * (24_000 * 4), 24_000, "float32")
        player = SoundDevicePlayer()
        worker = threading.Thread(target=player.play, args=(audio,))
        worker.start()
        stream = _FakeOutputStream.instances[0]
        self.assertTrue(stream.write_started.wait(timeout=1))

        player.stop()
        player.stop()
        worker.join(timeout=1)

        self.assertFalse(worker.is_alive())
        self.assertEqual(stream.abort_count, 1)
        self.assertTrue(stream.closed)

    def test_float_audio_normalization_targets_peak_without_changing_shape(self) -> None:
        samples = struct.pack("<3f", -0.0005, 0.00025, 0.00097)

        normalized = struct.unpack(
            "<3f", _normalize_float32_samples(samples)
        )

        self.assertAlmostEqual(max(abs(value) for value in normalized), 0.8)
        self.assertAlmostEqual(normalized[0], -0.8 * 0.0005 / 0.00097)
        self.assertAlmostEqual(normalized[1], 0.8 * 0.00025 / 0.00097)

    def test_float_audio_normalization_rejects_silent_or_invalid_buffers(self) -> None:
        for samples in (b"", b"\x00\x00", struct.pack("<2f", 0.0, 0.0)):
            with self.subTest(samples=samples):
                with self.assertRaises(VoiceSynthesisError):
                    _normalize_float32_samples(samples)

        with self.assertRaisesRegex(VoiceSynthesisError, "non-finite"):
            _normalize_float32_samples(struct.pack("<f", float("nan")))

    def test_local_tts_config_rewrites_remote_assets_to_verified_files(self) -> None:
        class FakeYaml:
            YAMLError = type("YAMLError", (Exception,), {})

            @staticmethod
            def safe_load(_content):
                return {
                    "weights_path": (
                        "hf://prasadvittaldev/pocket-tts-hindi/model.safetensors"
                    ),
                    "flow_lm": {
                        "lookup_table": {
                            "tokenizer_path": (
                                "hf://prasadvittaldev/pocket-tts-hindi/tokenizer.model"
                            )
                        }
                    },
                }

            @staticmethod
            def safe_dump(value, *, sort_keys):
                return json.dumps(value)

        with tempfile.TemporaryDirectory() as directory:
            tts_directory = Path(directory)
            for filename in (
                "config.yaml",
                "model_bf16.safetensors",
                "tokenizer.model",
            ):
                (tts_directory / filename).write_text("asset", encoding="utf-8")

            _write_local_tts_config(tts_directory, FakeYaml)
            local_config = json.loads(
                (tts_directory / "config.local.yaml").read_text(encoding="utf-8")
            )

        self.assertEqual(
            local_config["weights_path"],
            str(tts_directory / "model_bf16.safetensors"),
        )
        self.assertEqual(
            local_config["flow_lm"]["lookup_table"]["tokenizer_path"],
            str(tts_directory / "tokenizer.model"),
        )

    def test_push_to_talk_opens_microphone_only_after_start_confirmation(self) -> None:
        events: list[str] = []

        class FakeStream:
            def __init__(self, *, callback, **_kwargs) -> None:
                self.callback = callback

            def __enter__(self):
                events.append("microphone opened")
                self.callback(b"\x01\x00" * 4, 4, None, None)
                return self

            def __exit__(self, *_args) -> None:
                events.append("microphone closed")
                return None

        fake_sounddevice = types.ModuleType("sounddevice")
        fake_sounddevice.RawInputStream = FakeStream
        fake_sounddevice.CallbackStop = type("CallbackStop", (Exception,), {})
        fake_sounddevice.PortAudioError = type("PortAudioError", (Exception,), {})
        outputs: list[str] = []
        with patch.dict(sys.modules, {"sounddevice": fake_sounddevice}):
            audio = MicrophoneRecorder(
                60,
                input_func=lambda: events.append("enter"),
                output=outputs.append,
            ).record()

        self.assertEqual(
            events,
            ["enter", "microphone opened", "enter", "microphone closed"],
        )
        self.assertEqual(audio.samples, b"\x01\x00" * 4)
        self.assertEqual(audio.sample_rate, 16_000)
        self.assertTrue(any("push-to-talk" in item for item in outputs))

    def test_microphone_open_error_includes_permission_guidance(self) -> None:
        class FakePortAudioError(Exception):
            pass

        class FailingStream:
            def __init__(self, **_kwargs) -> None:
                pass

            def __enter__(self):
                raise FakePortAudioError("access denied")

            def __exit__(self, *_args) -> None:
                return None

        fake_sounddevice = types.ModuleType("sounddevice")
        fake_sounddevice.RawInputStream = FailingStream
        fake_sounddevice.CallbackStop = type("CallbackStop", (Exception,), {})
        fake_sounddevice.PortAudioError = FakePortAudioError
        with patch.dict(sys.modules, {"sounddevice": fake_sounddevice}):
            recorder = MicrophoneRecorder(
                60,
                input_func=lambda: None,
                output=lambda _text: None,
            )
            with self.assertRaisesRegex(VoiceDeviceError, "Windows microphone"):
                recorder.record()

    def test_recognizer_json_result_is_parsed_without_logging_transcript(self) -> None:
        self.assertEqual(
            _read_asr_text('{"file":"input.wav","text":"नमस्ते"}\n'),
            "नमस्ते",
        )
        with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            _read_asr_text("not json\n")

    def test_runtime_archive_rejects_paths_outside_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "unsafe.zip"
            destination = Path(directory) / "extract"
            destination.mkdir()
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "unsafe")
            with zipfile.ZipFile(archive_path) as archive:
                with self.assertRaisesRegex(ValueError, "outside"):
                    _safe_extract(archive, destination)


if __name__ == "__main__":
    unittest.main()
