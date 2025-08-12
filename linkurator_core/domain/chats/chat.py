from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    role: ChatRole
    content: str
    timestamp: datetime

    @classmethod
    def new_user_message(cls, content: str) -> ChatMessage:
        return cls(
            role=ChatRole.USER,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )

    @classmethod
    def new_assistant_message(cls, content: str) -> ChatMessage:
        return cls(
            role=ChatRole.ASSISTANT,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )


@dataclass
class Chat:
    uuid: UUID
    user_id: UUID
    title: str
    messages: list[ChatMessage]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, uuid: UUID, user_id: UUID, title: str) -> Chat:
        now = datetime.now(timezone.utc)
        return cls(
            uuid=uuid,
            user_id=user_id,
            title=title,
            messages=[],
            created_at=now,
            updated_at=now,
        )

    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)

    def add_user_message(self, content: str) -> None:
        message = ChatMessage.new_user_message(content)
        self.add_message(message)

    def add_assistant_message(self, content: str) -> None:
        message = ChatMessage.new_assistant_message(content)
        self.add_message(message)

    def update_title(self, title: str) -> None:
        self.title = title
        self.updated_at = datetime.now(timezone.utc)
