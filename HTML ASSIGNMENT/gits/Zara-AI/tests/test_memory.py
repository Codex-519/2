from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import httpx

from zara_ai.config import AppConfig, GenerationConfig, OllamaConfig
from zara_ai.conversation.engine import ConversationEngine
from zara_ai.conversation.ollama import OllamaClient
from zara_ai.memory.commands import handle_memory_command
from zara_ai.memory.store import (
    CURRENT_SCHEMA_VERSION,
    MemoryConsentError,
    MemoryNotFoundError,
    MemoryStore,
)


def _line(content: str = "", *, done: bool = False) -> bytes:
    return (
        json.dumps({"message": {"content": content}, "done": done}) + "\n"
    ).encode()


class MemoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "memory.sqlite3"
        self.store = MemoryStore(self.database_path)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_database_migration_starts_at_current_version_with_memory_off(self) -> None:
        self.assertEqual(self.store.schema_version, CURRENT_SCHEMA_VERSION)
        self.assertFalse(self.store.enabled)
        self.assertEqual(self.store.list_memories(), ())

    def test_consent_is_required_for_add_and_edit(self) -> None:
        with self.assertRaises(MemoryConsentError):
            self.store.add("I prefer concise replies")
        self.store.enable()
        memory = self.store.add("I prefer concise replies")
        self.store.disable()
        with self.assertRaises(MemoryConsentError):
            self.store.update(memory.id, "I prefer detailed replies")
        self.assertEqual(self.store.list_memories()[0].content, "I prefer concise replies")

    def test_crud_and_timestamps(self) -> None:
        self.store.enable()
        memory = self.store.add("  I prefer concise replies  ")
        self.assertEqual(memory.content, "I prefer concise replies")
        updated = self.store.update(memory.id, "I prefer detailed replies")
        self.assertEqual(updated.content, "I prefer detailed replies")
        self.assertEqual(updated.id, memory.id)
        self.assertEqual(updated.created_at, memory.created_at)
        self.assertGreaterEqual(updated.updated_at, memory.updated_at)
        self.assertEqual(self.store.list_memories(), (updated,))

        self.store.delete(memory.id)
        self.assertEqual(self.store.list_memories(), ())
        with self.assertRaises(MemoryNotFoundError):
            self.store.delete(memory.id)

    def test_consent_and_memories_persist_when_database_is_reopened(self) -> None:
        self.store.enable()
        saved = self.store.add("I prefer Hindi replies")
        reopened = MemoryStore(self.database_path)
        self.assertTrue(reopened.enabled)
        self.assertEqual(reopened.list_memories(), (saved,))
        reopened.disable()
        self.assertFalse(MemoryStore(self.database_path).enabled)

    def test_clear_deletes_every_memory_and_returns_count(self) -> None:
        self.store.enable()
        self.store.add("First")
        self.store.add("Second")
        self.store.disable()
        self.assertEqual(self.store.clear(), 2)
        self.assertEqual(self.store.list_memories(), ())
        self.assertFalse(self.store.enabled)

    def test_rejects_empty_memory_content(self) -> None:
        self.store.enable()
        with self.assertRaises(ValueError):
            self.store.add("  ")
        with self.assertRaises(ValueError):
            self.store.update(1, "")

    def test_refuses_database_created_by_newer_schema(self) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")
        finally:
            connection.close()
        with self.assertRaisesRegex(RuntimeError, "newer than the supported schema"):
            MemoryStore(self.database_path)


class MemoryCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp_directory.name) / "memory.sqlite3")
        self.outputs: list[str] = []
        self.confirmations: list[str] = []

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def _confirm(self, answer: str):
        def confirm(prompt: str) -> str:
            self.confirmations.append(prompt)
            return answer

        return confirm

    def test_opt_in_and_memory_saving_each_require_explicit_user_action(self) -> None:
        handled = handle_memory_command(
            "/remember I prefer short replies",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("y"),
        )
        self.assertTrue(handled)
        self.assertFalse(self.store.enabled)
        self.assertEqual(self.store.list_memories(), ())
        self.assertEqual(self.confirmations, [])

        handle_memory_command(
            "/memory-on",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("y"),
        )
        self.assertTrue(self.store.enabled)
        self.assertEqual(self.store.list_memories(), ())

        handle_memory_command(
            "/remember I prefer short replies",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("n"),
        )
        self.assertEqual(self.store.list_memories(), ())
        self.assertIn("Do not save sensitive information", self.confirmations[-1])

        handle_memory_command(
            "/remember I prefer short replies",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("y"),
        )
        self.assertEqual(self.store.list_memories()[0].content, "I prefer short replies")

    def test_edit_delete_clear_commands_require_confirmation(self) -> None:
        self.store.enable()
        memory = self.store.add("Original")

        handle_memory_command(
            f"/edit-memory {memory.id} Updated",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("n"),
        )
        self.assertEqual(self.store.list_memories()[0].content, "Original")

        handle_memory_command(
            f"/edit-memory {memory.id} Updated",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("y"),
        )
        self.assertEqual(self.store.list_memories()[0].content, "Updated")

        handle_memory_command(
            f"/forget {memory.id}",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("n"),
        )
        self.assertEqual(len(self.store.list_memories()), 1)
        handle_memory_command(
            f"/forget {memory.id}",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("y"),
        )
        self.assertEqual(self.store.list_memories(), ())

        self.store.add("One")
        self.store.add("Two")
        handle_memory_command(
            "/clear-memories",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("n"),
        )
        self.assertEqual(len(self.store.list_memories()), 2)
        handle_memory_command(
            "/clear-memories",
            self.store,
            output=self.outputs.append,
            confirm=self._confirm("y"),
        )
        self.assertEqual(self.store.list_memories(), ())

    def test_memory_list_is_user_visible_and_unknown_command_is_untouched(self) -> None:
        self.store.enable()
        memory = self.store.add("I prefer concise answers")
        self.assertFalse(
            handle_memory_command(
                "hello",
                self.store,
                output=self.outputs.append,
            )
        )
        self.assertTrue(
            handle_memory_command(
                "/memories",
                self.store,
                output=self.outputs.append,
            )
        )
        self.assertEqual(self.outputs, [f"[{memory.id}] I prefer concise answers"])


class MemoryConversationTests(unittest.IsolatedAsyncioTestCase):
    async def test_opted_in_memories_are_separate_context_not_saved_history(self) -> None:
        temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(temp_directory.name) / "memory.sqlite3"
        store = MemoryStore(database_path)
        store.enable()
        store.add("I prefer concise replies")
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, content=_line("Sure.") + _line(done=True))

        client = OllamaClient(
            AppConfig(
                ollama=OllamaConfig(),
                generation=GenerationConfig(),
            ),
            transport=httpx.MockTransport(handler),
        )
        engine = ConversationEngine(client, store)
        try:
            _ = [chunk async for chunk in engine.stream("My phone number is sensitive")]
            messages = requests[0]["messages"]
            self.assertEqual(messages[0]["role"], "system")
            self.assertIn("You are Zara", messages[0]["content"])
            self.assertEqual(messages[1]["role"], "system")
            self.assertIn("I prefer concise replies", messages[1]["content"])
            self.assertIn("not as instructions", messages[1]["content"])
            self.assertNotIn("My phone number", messages[1]["content"])
            self.assertEqual(messages[-1]["content"], "My phone number is sensitive")
            self.assertEqual(
                [message.content for message in engine.history],
                ["My phone number is sensitive", "Sure."],
            )
            self.assertEqual(
                [memory.content for memory in store.list_memories()],
                ["I prefer concise replies"],
            )

            store.disable()
            _ = [chunk async for chunk in engine.stream("Another question")]
            self.assertEqual(len(requests[1]["messages"]), 4)
            self.assertEqual(requests[1]["messages"][1]["role"], "user")
            self.assertNotIn(
                "I prefer concise replies",
                json.dumps(requests[1]["messages"]),
            )
            self.assertEqual(len(store.list_memories()), 1)
        finally:
            await client.aclose()
            temp_directory.cleanup()


if __name__ == "__main__":
    unittest.main()
