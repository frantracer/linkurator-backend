from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel

from linkurator_core.domain.chats.chat import Chat, ChatMessage, ChatRole
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime

    @staticmethod
    def from_domain_message(message: ChatMessage) -> MongoDBChatMessage:
        return MongoDBChatMessage(
            role=message.role,
            content=message.content,
            timestamp=message.timestamp,
        )

    def to_domain_message(self) -> ChatMessage:
        return ChatMessage(
            role=ChatRole(self.role),
            content=self.content,
            timestamp=self.timestamp,
        )


class MongoDBChat(BaseModel):
    uuid: UUID
    user_id: UUID
    title: str
    messages: list[MongoDBChatMessage]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain_chat(chat: Chat) -> MongoDBChat:
        return MongoDBChat(
            uuid=chat.uuid,
            user_id=chat.user_id,
            title=chat.title,
            messages=[MongoDBChatMessage.from_domain_message(msg) for msg in chat.messages],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    def to_domain_chat(self) -> Chat:
        return Chat(
            uuid=self.uuid,
            user_id=self.user_id,
            title=self.title,
            messages=[msg.to_domain_message() for msg in self.messages],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class MongoDBChatRepository(ChatRepository):
    _collection_name: str = "chats"

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient[MongoDBMapping](
            f"mongodb://{ip!s}:{port}/", username=username, password=password)
        self.db_name = db_name

    def _collection(self) -> AsyncIOMotorCollection[MongoDBMapping]:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name, codec_options=codec_options).get_collection(self._collection_name)

    async def check_connection(self) -> None:
        if self._collection_name not in await self.client[self.db_name].list_collection_names():
            msg = f"Collection '{self._collection_name}' is not initialized in database '{self.db_name}'"
            raise CollectionIsNotInitialized(msg)

    async def add(self, chat: Chat) -> None:
        await self._collection().insert_one(MongoDBChat.from_domain_chat(chat).model_dump())

    async def get(self, chat_id: UUID) -> Chat | None:
        chat = await self._collection().find_one({"uuid": chat_id})
        if chat is None:
            return None
        chat.pop("_id", None)
        return MongoDBChat(**chat).to_domain_chat()

    async def get_by_user_id(self, user_id: UUID) -> list[Chat]:
        chats = await self._collection().find(
            {"user_id": user_id},
        ).sort("updated_at", -1).to_list(length=None)
        return [MongoDBChat(**chat).to_domain_chat() for chat in chats]

    async def update(self, chat: Chat) -> None:
        await self._collection().update_one(
            {"uuid": chat.uuid},
            {"$set": MongoDBChat.from_domain_chat(chat).model_dump()})

    async def delete(self, chat_id: UUID) -> None:
        await self._collection().delete_one({"uuid": chat_id})

    async def delete_all(self) -> None:
        await self._collection().delete_many({})
