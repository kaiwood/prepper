from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, TypedDict

Role = Literal["user", "assistant"]


class ChatMessage(TypedDict):
    role: Role
    content: str


def _normalize_content(content: str, *, allow_empty: bool = False) -> str:
    normalized = content.strip()
    if not allow_empty and not normalized:
        raise ValueError("message content is required")
    return normalized


@dataclass
class Conversation:
    _messages: list[ChatMessage] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        self._messages.append(
            {
                "role": "user",
                "content": _normalize_content(content),
            }
        )

    def add_assistant_reply(self, content: str) -> None:
        normalized = _normalize_content(content, allow_empty=True)
        if normalized:
            self._messages.append(
                {
                    "role": "assistant",
                    "content": normalized,
                }
            )

    def replace_last_assistant_reply(self, content: str) -> None:
        normalized = _normalize_content(content, allow_empty=True)
        if not normalized:
            return

        for index in range(len(self._messages) - 1, -1, -1):
            if self._messages[index]["role"] == "assistant":
                self._messages[index]["content"] = normalized
                return

    def get_messages(self) -> list[ChatMessage]:
        return [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in self._messages
        ]

    def get_recent_messages(self, limit: int = 10) -> list[ChatMessage]:
        if limit <= 0:
            return []
        return [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in self._messages[-limit:]
        ]

    @classmethod
    def from_messages(cls, messages: Iterable[dict[str, str]]) -> "Conversation":
        conversation = cls()

        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("conversation_history must contain objects")

            role = message.get("role")
            content = message.get("content", "")
            if not isinstance(content, str):
                raise ValueError("conversation_history content must be a string")

            if role == "user":
                conversation.add_user_message(content)
            elif role == "assistant":
                conversation.add_assistant_reply(content)
            else:
                raise ValueError("conversation_history contains an invalid role")

        return conversation
