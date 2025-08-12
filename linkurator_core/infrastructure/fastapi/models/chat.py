from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from linkurator_core.domain.chats.chat import Chat, ChatMessage


class ChatMessageResponse(BaseModel):
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(description="Message timestamp")

    @classmethod
    def from_domain(cls, message: ChatMessage) -> "ChatMessageResponse":
        return cls(
            role=message.role,
            content=message.content,
            timestamp=message.timestamp,
        )


class ChatResponse(BaseModel):
    uuid: UUID = Field(description="Chat unique identifier")
    user_id: UUID = Field(description="User ID who owns the chat")
    title: str = Field(description="Chat title")
    messages: list[ChatMessageResponse] = Field(description="Chat messages")
    created_at: datetime = Field(description="Chat creation timestamp")
    updated_at: datetime = Field(description="Chat last update timestamp")

    @classmethod
    def from_domain(cls, chat: Chat) -> "ChatResponse":
        return cls(
            uuid=chat.uuid,
            user_id=chat.user_id,
            title=chat.title,
            messages=[ChatMessageResponse.from_domain(msg) for msg in chat.messages],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )


class CreateChatRequest(BaseModel):
    title: str = Field(description="Chat title", min_length=1, max_length=200)


class CreateChatResponse(BaseModel):
    chat: ChatResponse = Field(description="Created chat")

    @classmethod
    def from_domain(cls, chat: Chat) -> "CreateChatResponse":
        return cls(
            chat=ChatResponse.from_domain(chat),
        )


class ChatSummaryResponse(BaseModel):
    uuid: UUID = Field(description="Chat unique identifier")
    user_id: UUID = Field(description="User ID who owns the chat")
    title: str = Field(description="Chat title")
    created_at: datetime = Field(description="Chat creation timestamp")
    updated_at: datetime = Field(description="Chat last update timestamp")

    @classmethod
    def from_domain(cls, chat: Chat) -> "ChatSummaryResponse":
        return cls(
            uuid=chat.uuid,
            user_id=chat.user_id,
            title=chat.title,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )


class GetUserChatsResponse(BaseModel):
    chats: list[ChatSummaryResponse] = Field(description="List of user chats")

    @classmethod
    def from_domain(cls, chats: list[Chat]) -> "GetUserChatsResponse":
        return cls(
            chats=[ChatSummaryResponse.from_domain(chat) for chat in chats],
        )
