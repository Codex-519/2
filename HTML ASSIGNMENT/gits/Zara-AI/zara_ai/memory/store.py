"""Local SQLite memory with explicit consent and CRUD operations."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


CURRENT_SCHEMA_VERSION = 1


class MemoryConsentError(RuntimeError):
    """Raised when a memory write is attempted without opt-in."""


class MemoryNotFoundError(LookupError):
    """Raised when a requested memory does not exist."""


@dataclass(frozen=True, slots=True)
class Memory:
    id: int
    content: str
    created_at: str
    updated_at: str


def default_memory_path() -> Path:
    """Return the per-user, local application-data database path."""
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError(
                "LOCALAPPDATA is not set; cannot locate Zara AI memory."
            )
        return Path(local_app_data) / "ZaraAI" / "memory.sqlite3"
    return Path.home() / ".local" / "share" / "zara-ai" / "memory.sqlite3"


class MemoryStore:
    """Manage consent and user-approved memories in a local SQLite database."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_memory_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > CURRENT_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Memory database schema {version} is newer than the "
                    f"supported schema {CURRENT_SCHEMA_VERSION}."
                )
            if version == 0:
                connection.executescript(
                    """
                    BEGIN IMMEDIATE;
                    CREATE TABLE memories (
                        id INTEGER PRIMARY KEY,
                        content TEXT NOT NULL CHECK (length(trim(content)) > 0),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    INSERT INTO settings (key, value)
                    VALUES ('memory_enabled', '0');
                    PRAGMA user_version = 1;
                    COMMIT;
                    """
                )

    @property
    def enabled(self) -> bool:
        """Whether the user has explicitly opted in to memory context."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = 'memory_enabled'"
            ).fetchone()
        if row is None:
            raise RuntimeError("Memory consent setting is missing from the database.")
        if row["value"] not in {"0", "1"}:
            raise RuntimeError("Memory consent setting has an invalid value.")
        return row["value"] == "1"

    @property
    def schema_version(self) -> int:
        """The database schema version, for diagnostics and migration tests."""
        with self._connection() as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    def enable(self) -> None:
        """Opt in to using saved memories as local conversation context."""
        self._set_enabled(True)

    def disable(self) -> None:
        """Opt out; saved items remain manageable but are not sent to the model."""
        self._set_enabled(False)

    def _set_enabled(self, enabled: bool) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE settings SET value = ? WHERE key = 'memory_enabled'",
                ("1" if enabled else "0",),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Could not update the memory consent setting.")

    def list_memories(self) -> tuple[Memory, ...]:
        """Return all saved memories in stable creation order."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, content, created_at, updated_at
                FROM memories
                ORDER BY id
                """
            ).fetchall()
        return tuple(_to_memory(row) for row in rows)

    def add(self, content: str) -> Memory:
        """Save explicitly provided content after opt-in."""
        normalized = _validate_content(content)
        self._require_enabled()
        now = _now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories (content, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (normalized, now, now),
            )
            row = connection.execute(
                """
                SELECT id, content, created_at, updated_at
                FROM memories WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
        if row is None:
            raise RuntimeError("Memory was inserted but could not be retrieved.")
        return _to_memory(row)

    def update(self, memory_id: int, content: str) -> Memory:
        """Replace one saved memory after explicit user approval."""
        normalized = _validate_content(content)
        self._require_enabled()
        now = _now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE memories
                SET content = ?, updated_at = ?
                WHERE id = ?
                """,
                (normalized, now, memory_id),
            )
            if cursor.rowcount != 1:
                raise MemoryNotFoundError(f"Memory {memory_id} was not found.")
            row = connection.execute(
                """
                SELECT id, content, created_at, updated_at
                FROM memories WHERE id = ?
                """,
                (memory_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("Updated memory could not be retrieved.")
        return _to_memory(row)

    def delete(self, memory_id: int) -> None:
        """Delete one saved memory; deleting is allowed while opted out."""
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,)
            )
        if cursor.rowcount != 1:
            raise MemoryNotFoundError(f"Memory {memory_id} was not found.")

    def clear(self) -> int:
        """Delete all saved memories and return the number removed."""
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM memories")
        return cursor.rowcount

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise MemoryConsentError(
                "Memory is off. Opt in with /memory-on before adding or editing."
            )


def _validate_content(content: str) -> str:
    if not isinstance(content, str):
        raise TypeError("Memory content must be text.")
    normalized = content.strip()
    if not normalized:
        raise ValueError("Memory content must not be empty.")
    return normalized


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _to_memory(row: sqlite3.Row) -> Memory:
    return Memory(
        id=int(row["id"]),
        content=str(row["content"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
