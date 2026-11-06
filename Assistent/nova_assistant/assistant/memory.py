"""Short-term conversation memory for the current Nova session."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str


class ConversationMemory:
    def __init__(self, max_turns: int = 12) -> None:
        self.max_messages = max(2, max_turns * 2)
        self._messages: list[Message] = []

    def add(self, role: str, content: str) -> None:
        self._messages.append(Message(role=role, content=content))
        self._messages = self._messages[-self.max_messages :]

    def as_dicts(self) -> list[dict[str, str]]:
        return [{"role": item.role, "content": item.content} for item in self._messages]

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)