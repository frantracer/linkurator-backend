from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel

from linkurator_core.domain.topics.followed_topic import FollowedTopic
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping


class MongoDBFollowedTopic(BaseModel):
    user_uuid: UUID
    topic_uuid: UUID
    created_at: datetime

    def to_domain_followed_topic(self) -> FollowedTopic:
        return FollowedTopic(
            user_uuid=self.user_uuid,
            topic_uuid=self.topic_uuid,
            created_at=self.created_at
        )


class MongoDBFollowedTopicsRepository(FollowedTopicsRepository):
    _collection_name: str = 'followed_topics'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient[MongoDBMapping](
            f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

    def _collection(self) -> AsyncIOMotorCollection[MongoDBMapping]:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name, codec_options=codec_options).get_collection(self._collection_name)

    async def get_followed_topics(self, user_uuid: UUID) -> list[FollowedTopic]:
        return [MongoDBFollowedTopic(**followed_topic).to_domain_followed_topic()
                async for followed_topic
                in self._collection().find({'user_uuid': user_uuid})]

    async def follow_topic(self, user_id: UUID, topic_id: UUID) -> None:
        await self._collection().insert_one({
            'user_uuid': user_id,
            'topic_uuid': topic_id,
            'created_at': datetime.utcnow()
        })

    async def unfollow_topic(self, user_uuid: UUID, topic_uuid: UUID) -> None:
        await self._collection().delete_one({'user_uuid': user_uuid, 'topic_uuid': topic_uuid})
