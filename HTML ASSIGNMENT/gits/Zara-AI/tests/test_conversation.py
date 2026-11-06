from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

import httpx

from zara_ai.config import (
    AppConfig,
    GenerationConfig,
    OllamaConfig,
    load_config,
)
from zara_ai.conversation.engine import ConversationEngine, ConversationState
from zara_ai.conversation.errors import (
    OllamaConnectionError,
    OllamaProtocolError,
    OllamaResponseError,
)
from zara_ai.conversation.ollama import OllamaClient


def _line(content: str = "", *, done: bool = False) -> bytes:
    return (
        json.dumps({"message": {"content": content}, "done": done}) + "\n"
    ).encode()


def _client(
    handler,
    *,
    model: str = "qwen2.5:7b",
) -> OllamaClient:
    config = AppConfig(
        ollama=OllamaConfig(model=model),
        generation=GenerationConfig(temperature=0.4, num_ctx=2048),
    )
    return OllamaClient(config, transport=httpx.MockTransport(handler))


class _AsyncBody(httpx.AsyncByteStream):
    def __init__(self, body) -> None:
        self._body = body

    async def __aiter__(self):
        async for chunk in self._body:
            yield chunk


class ConversationTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_and_commits_completed_exchange(self) -> None:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(
                200,
                content=_line("Namaste") + _line("!") + _line(done=True),
            )

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            chunks = [chunk async for chunk in engine.stream("Hello")]
            self.assertEqual(chunks, ["Namaste", "!"])
            self.assertEqual(engine.state, ConversationState.COMPLETED)
            self.assertEqual(
                [(message.role, message.content) for message in engine.history],
                [("user", "Hello"), ("assistant", "Namaste!")],
            )
            self.assertEqual(requests[0]["model"], "qwen2.5:7b")
            self.assertEqual(requests[0]["options"]["num_ctx"], 2048)
            self.assertTrue(requests[0]["stream"])
            self.assertEqual(requests[0]["messages"][0]["role"], "system")
            self.assertIn("You are Zara", requests[0]["messages"][0]["content"])
            self.assertEqual(requests[0]["messages"][1]["content"], "Hello")
        finally:
            await client.aclose()

    async def test_sends_completed_history_on_next_turn(self) -> None:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, content=_line("Reply") + _line(done=True))

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            _ = [chunk async for chunk in engine.stream("First")]
            _ = [chunk async for chunk in engine.stream("Second")]
            self.assertEqual(
                [
                    message["content"]
                    for message in requests[1]["messages"]
                    if message["role"] != "system"
                ],
                ["First", "Reply", "Second"],
            )
            self.assertEqual(requests[0]["messages"][0], requests[1]["messages"][0])
        finally:
            await client.aclose()

    async def test_system_prompt_enforces_zara_identity(self) -> None:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, content=_line("Main Zara hoon.") + _line(done=True))

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            reply = "".join([chunk async for chunk in engine.stream("Tum kaun ho?")])
            system_prompt = requests[0]["messages"][0]["content"]
            self.assertEqual(reply, "Main Zara hoon.")
            self.assertIn("identity are always Zara", system_prompt)
            self.assertIn("never say you are that model", system_prompt)
            self.assertIn("Alibaba Cloud", system_prompt)
            self.assertIn("Main Zara hoon, tumhari local AI assistant.", system_prompt)
            self.assertNotIn("Hey Zara", reply)
        finally:
            await client.aclose()

    async def test_hinglish_prompt_and_response_are_preserved(self) -> None:
        requests = []
        hinglish_reply = "Haan, main ismein tumhari help kar sakti hoon."

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, content=_line(hinglish_reply) + _line(done=True))

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            chunks = [chunk async for chunk in engine.stream("Mujhe ismein help chahiye")]
            system_prompt = requests[0]["messages"][0]["content"]
            self.assertEqual("".join(chunks), hinglish_reply)
            self.assertIn("including Hindi or Hinglish", system_prompt)
            self.assertIn("natural conversational Romanized Hindi or Hinglish", system_prompt)
            self.assertIn("Avoid stiff, overly formal, or Sanskritized wording", system_prompt)
            self.assertIn("main help kar sakti hoon", system_prompt)
            self.assertIn("Speak naturally in the language and style the user uses", system_prompt)
            self.assertEqual(requests[0]["messages"][-1]["content"], "Mujhe ismein help chahiye")
        finally:
            await client.aclose()

    async def test_turn_instruction_is_additive_to_zara_identity(self) -> None:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, content=_line("नमस्ते") + _line(done=True))

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            reply = "".join(
                [
                    chunk
                    async for chunk in engine.stream(
                        "Namaste",
                        system_instruction="Reply in Devanagari for Hindi TTS.",
                    )
                ]
            )
            messages = requests[0]["messages"]
            self.assertEqual(reply, "नमस्ते")
            self.assertIn("You are Zara", messages[0]["content"])
            self.assertEqual(
                messages[1]["content"],
                "Reply in Devanagari for Hindi TTS.",
            )
            self.assertEqual(messages[2]["content"], "Namaste")
        finally:
            await client.aclose()

    async def test_interrupt_cancels_response_and_does_not_commit_partial_turn(
        self,
    ) -> None:
        started = asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            async def body():
                yield _line("Partial")
                started.set()
                await asyncio.Event().wait()

            return httpx.Response(200, stream=_AsyncBody(body()))

        client = _client(handler)
        engine = ConversationEngine(client)

        async def collect() -> list[str]:
            return [chunk async for chunk in engine.stream("Stop me")]

        task = asyncio.create_task(collect())
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
            self.assertEqual(engine.state, ConversationState.STREAMING)
            self.assertTrue(engine.interrupt())
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(engine.state, ConversationState.INTERRUPTED)
            self.assertEqual(engine.history, ())
            self.assertFalse(engine.interrupt())
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await client.aclose()

    async def test_provider_error_sets_error_state_without_saving_turn(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=(json.dumps({"error": "model is not installed"}) + "\n").encode(),
            )

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            with self.assertRaises(OllamaResponseError):
                _ = [chunk async for chunk in engine.stream("Hello")]
            self.assertEqual(engine.state, ConversationState.ERROR)
            self.assertEqual(engine.history, ())
        finally:
            await client.aclose()

    async def test_invalid_stream_sets_error_state(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{not json}\n")

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            with self.assertRaises(OllamaProtocolError):
                _ = [chunk async for chunk in engine.stream("Hello")]
            self.assertEqual(engine.state, ConversationState.ERROR)
            self.assertEqual(engine.history, ())
        finally:
            await client.aclose()

    async def test_unavailable_server_error_is_actionable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline", request=request)

        client = _client(handler)
        try:
            with self.assertRaises(OllamaConnectionError):
                _ = [chunk async for chunk in client.stream_chat([])]
        finally:
            await client.aclose()

    async def test_lists_models_from_ollama(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/tags")
            return httpx.Response(
                200,
                json={"models": [{"name": "qwen2.5:7b"}, {"name": "sia:latest"}]},
            )

        client = _client(handler)
        try:
            self.assertEqual(
                await client.list_models(),
                ["qwen2.5:7b", "sia:latest"],
            )
        finally:
            await client.aclose()

    async def test_incomplete_stream_does_not_commit_turn(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=_line("Partial"))

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            with self.assertRaises(OllamaProtocolError):
                _ = [chunk async for chunk in engine.stream("Hello")]
            self.assertEqual(engine.state, ConversationState.ERROR)
            self.assertEqual(engine.history, ())
        finally:
            await client.aclose()

    async def test_rejects_empty_prompt_and_can_clear_history(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=_line("Reply") + _line(done=True))

        client = _client(handler)
        engine = ConversationEngine(client)
        try:
            with self.assertRaises(ValueError):
                _ = [chunk async for chunk in engine.stream("   ")]
            self.assertEqual(engine.state, ConversationState.IDLE)
            _ = [chunk async for chunk in engine.stream("Hello")]
            engine.clear_history()
            self.assertEqual(engine.history, ())
            self.assertEqual(engine.state, ConversationState.IDLE)
        finally:
            await client.aclose()


class ConfigurationTests(unittest.TestCase):
    def test_creates_default_config_and_loads_user_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            config = load_config(path)
            self.assertEqual(config.ollama.model, "qwen2.5:7b")
            self.assertEqual(config.generation.num_ctx, 4096)
            self.assertFalse(config.voice.enabled)
            self.assertEqual(config.voice.max_record_seconds, 60)
            self.assertEqual(
                config.voice.reference_wav,
                Path(__file__).resolve().parents[1]
                / "assets"
                / "voice_samples"
                / "speech-1792953435497.wav",
            )
            self.assertTrue(path.exists())
            path.write_text(
                '[ollama]\nmodel = "sia:latest"\n'
                '[generation]\ntemperature = 0.2\nnum_ctx = 1024\n'
                '[voice]\nenabled = true\nmax_record_seconds = 120\n'
                'data_directory = "voice-data"\n'
                'reference_wav = "samples/voice.wav"\n',
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.ollama.model, "sia:latest")
            self.assertEqual(config.generation.temperature, 0.2)
            self.assertEqual(config.generation.num_ctx, 1024)
            self.assertTrue(config.voice.enabled)
            self.assertEqual(config.voice.max_record_seconds, 120)
            self.assertEqual(config.voice.data_directory, Path("voice-data"))
            self.assertEqual(
                config.voice.reference_wav,
                (path.parent / "samples" / "voice.wav").resolve(),
            )

    def test_environment_overrides_model_and_server(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            load_config(path)
            old_model = os.environ.get("ZARA_OLLAMA_MODEL")
            old_url = os.environ.get("ZARA_OLLAMA_BASE_URL")
            try:
                os.environ["ZARA_OLLAMA_MODEL"] = "sia:latest"
                os.environ["ZARA_OLLAMA_BASE_URL"] = "http://localhost:11434/"
                config = load_config(path)
                self.assertEqual(config.ollama.model, "sia:latest")
                self.assertEqual(config.ollama.base_url, "http://localhost:11434")
            finally:
                if old_model is None:
                    os.environ.pop("ZARA_OLLAMA_MODEL", None)
                else:
                    os.environ["ZARA_OLLAMA_MODEL"] = old_model
                if old_url is None:
                    os.environ.pop("ZARA_OLLAMA_BASE_URL", None)
                else:
                    os.environ["ZARA_OLLAMA_BASE_URL"] = old_url

    def test_invalid_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[ollama]\nbase_url = "file:///tmp"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "base_url"):
                load_config(path)

    def test_invalid_voice_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                "[voice]\nenabled = true\nmax_record_seconds = 301\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "max_record_seconds"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
