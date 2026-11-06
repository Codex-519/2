"""Explicit, confirmation-based terminal controls for user memories."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

from zara_ai.memory.store import (
    MemoryConsentError,
    MemoryNotFoundError,
    MemoryStore,
)

Output = Callable[[str], None]
Confirm = Callable[[str], str]
logger = logging.getLogger(__name__)


def handle_memory_command(
    command: str,
    store: MemoryStore,
    *,
    output: Output = print,
    confirm: Confirm = input,
) -> bool:
    """Handle a memory command; return False for non-memory commands."""
    name, _, argument = command.strip().partition(" ")
    argument = argument.strip()
    try:
        if name == "/memory":
            status = "on" if store.enabled else "off"
            output(f"Long-term memory is {status}.")
            output("Conversation history remains separate and is not saved to memory.")
        elif name == "/memory-on":
            store.enable()
            output("Memory is on. No conversation is saved automatically.")
            output("Use /remember with explicit confirmation to save one memory.")
        elif name == "/memory-off":
            store.disable()
            output("Memory is off. Saved memories remain available to review and delete.")
        elif name == "/memories":
            memories = store.list_memories()
            if not memories:
                output("No saved memories.")
            for memory in memories:
                output(f"[{memory.id}] {memory.content}")
        elif name == "/remember":
            if not argument:
                output("Usage: /remember <memory text>")
            elif not store.enabled:
                raise MemoryConsentError(
                    "Memory is off. Opt in first with /memory-on."
                )
            elif _confirmed(
                confirm,
                "This saves only the text you entered to local SQLite. "
                "Do not save sensitive information. Save it? [y/N] ",
            ):
                memory = store.add(argument)
                output(f"Saved memory [{memory.id}].")
            else:
                output("Memory not saved.")
        elif name == "/edit-memory":
            memory_id, replacement = _parse_id_and_text(argument)
            if not store.enabled:
                raise MemoryConsentError(
                    "Memory is off. Opt in with /memory-on before editing."
                )
            if _confirmed(
                confirm,
                "This replaces the selected local memory. Do not store "
                "sensitive information. Confirm edit? [y/N] ",
            ):
                memory = store.update(memory_id, replacement)
                output(f"Updated memory [{memory.id}].")
            else:
                output("Memory unchanged.")
        elif name == "/forget":
            memory_id = _parse_id(argument)
            if _confirmed(
                confirm,
                f"Delete memory [{memory_id}] permanently? [y/N] ",
            ):
                store.delete(memory_id)
                output(f"Deleted memory [{memory_id}].")
            else:
                output("Memory kept.")
        elif name == "/clear-memories":
            if _confirmed(
                confirm,
                "Delete ALL long-term memories permanently? [y/N] ",
            ):
                count = store.clear()
                output(f"Deleted {count} memories.")
            else:
                output("Memories kept.")
        else:
            return False
    except (MemoryConsentError, MemoryNotFoundError, ValueError) as error:
        output(f"Memory error: {error}")
    except sqlite3.Error:
        logger.exception("Memory database operation failed.")
        output("Memory database error. Check the Zara AI log for details.")
    return True


def _confirmed(confirm: Confirm, prompt: str) -> bool:
    return confirm(prompt).strip().casefold() == "y"


def _parse_id(argument: str) -> int:
    try:
        return int(argument)
    except ValueError as error:
        raise ValueError("Provide a valid memory ID.") from error


def _parse_id_and_text(argument: str) -> tuple[int, str]:
    memory_id_text, separator, content = argument.partition(" ")
    if not separator or not content.strip():
        raise ValueError("Usage: /edit-memory <id> <replacement text>")
    return _parse_id(memory_id_text), content.strip()
