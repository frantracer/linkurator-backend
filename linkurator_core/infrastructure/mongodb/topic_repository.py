from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import List, Optional, Any
from uuid import UUID

import pymongo
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from pydantic import BaseModel
from pymongo import MongoClient

from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBTopic(BaseModel):
    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: List[UUID]
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
            updated_at=topic.updated_at
        )

    def to_domain_topic(self) -> Topic:
        return Topic(
            uuid=self.uuid,
            name=self.name,
            subscriptions_ids=self.subscriptions_ids,
            user_id=self.user_id,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class MongoDBTopicRepository(TopicRepository):
    client: MongoClient[Any]
    db_name: str
    _collection_name: str = 'topics'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, topic: Topic) -> None:
        collection = self._topic_collection()
        try:
            collection.insert_one(MongoDBTopic.from_domain_topic(topic).model_dump())
        except pymongo.errors.DuplicateKeyError as err:
            raise DuplicatedKeyError(f"Topic with id '{topic.uuid}' already exists") from err

    def get(self, topic_id: UUID) -> Optional[Topic]:
        collection = self._topic_collection()
        topic: Optional[dict[str, Any]] = collection.find_one({'uuid': topic_id})
        if topic is None:
            return None
        return MongoDBTopic(**topic).to_domain_topic()

    def update(self, topic: Topic) -> None:
        collection = self._topic_collection()
        collection.update_one({'uuid': topic.uuid}, {'$set': MongoDBTopic.from_domain_topic(topic).model_dump()})

    def delete(self, topic_id: UUID) -> None:
        collection = self._topic_collection()
        collection.delete_one({'uuid': topic_id})

    def get_by_user_id(self, user_id: UUID) -> List[Topic]:
        collection = self._topic_collection()
        topics = collection.find({'user_id': user_id})
        return [MongoDBTopic(**topic).to_domain_topic() for topic in topics]

    def _topic_collection(self) -> Any:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            self._collection_name,
            codec_options=codec_options)
