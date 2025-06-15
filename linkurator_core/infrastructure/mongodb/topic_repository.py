from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

import pymongo
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel

from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping, normalize_text_search
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBTopic(BaseModel):
    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: list[UUID]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain_topic(topic: Topic) -> MongoDBTopic:
        return MongoDBTopic(
            uuid=topic.uuid,
            name=topic.name,
            subscriptions_ids=topic.subscriptions_ids,
            user_id=topic.user_id,
            created_at=topic.created_at,
            updated_at=topic.updated_at,
        )

    def to_domain_topic(self) -> Topic:
        return Topic(
            uuid=self.uuid,
            name=self.name,
            subscriptions_ids=self.subscriptions_ids,
            user_id=self.user_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class MongoDBTopicRepository(TopicRepository):
    _collection_name: str = "topics"

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient[MongoDBMapping](
            f"mongodb://{ip!s}:{port}/", username=username, password=password)
        self.db_name = db_name

    def _topic_collection(self) -> AsyncIOMotorCollection[MongoDBMapping]:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name, codec_options=codec_options).get_collection(self._collection_name)

    async def check_connection(self) -> None:
        if self._collection_name not in await self.client[self.db_name].list_collection_names():
            msg = f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'"
            raise CollectionIsNotInitialized(
                msg)

    async def add(self, topic: Topic) -> None:
        collection = self._topic_collection()
        try:
            await collection.insert_one(MongoDBTopic.from_domain_topic(topic).model_dump())
        except pymongo.errors.DuplicateKeyError as err:
            msg = f"Topic with id '{topic.uuid}' already exists"
            raise DuplicatedKeyError(msg) from err

    async def get(self, topic_id: UUID) -> Topic | None:
        collection = self._topic_collection()
        topic: dict[str, Any] | None = await collection.find_one({"uuid": topic_id})
        if topic is None:
            return None
        return MongoDBTopic(**topic).to_domain_topic()

    async def find_topics(self, topic_ids: list[UUID]) -> list[Topic]:
        collection = self._topic_collection()
        topics = await collection.find({"uuid": {"$in": topic_ids}}).to_list(length=None)
        return [MongoDBTopic(**topic).to_domain_topic() for topic in topics]

    async def find_topics_by_name(self, name: str) -> list[Topic]:
        collection = self._topic_collection()
        topics: list[dict[str, Any]] = await (collection.find(
            {"$text": {"$search": normalize_text_search(name)}},
        ).sort("created_at", pymongo.DESCENDING).to_list(length=None))
        return [MongoDBTopic(**topic).to_domain_topic() for topic in topics]

    async def update(self, topic: Topic) -> None:
        collection = self._topic_collection()
        await collection.update_one({"uuid": topic.uuid}, {"$set": MongoDBTopic.from_domain_topic(topic).model_dump()})

    async def delete(self, topic_id: UUID) -> None:
        collection = self._topic_collection()
        await collection.delete_one({"uuid": topic_id})

    async def delete_all(self) -> None:
        collection = self._topic_collection()
        await collection.delete_many({})

    async def get_by_user_id(self, user_id: UUID) -> list[Topic]:
        collection = self._topic_collection()
        topics = await collection.find({"user_id": user_id}).to_list(length=None)
        return [MongoDBTopic(**topic).to_domain_topic() for topic in topics]
