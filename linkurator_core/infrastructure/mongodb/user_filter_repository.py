from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel

from linkurator_core.domain.users.user_filter import UserFilter
from linkurator_core.domain.users.user_filter_repository import UserFilterRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBUserFilter(BaseModel):
    user_id: UUID
    text_filter: str | None = None
    min_duration: int | None = None
    max_duration: int | None = None
    include_items_without_interactions: bool = True
    include_recommended_items: bool = True
    include_discouraged_items: bool = True
    include_viewed_items: bool = True
    include_hidden_items: bool = True
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain(filter_obj: UserFilter) -> MongoDBUserFilter:
        return MongoDBUserFilter(
            user_id=filter_obj.user_id,
            text_filter=filter_obj.text_filter,
            min_duration=filter_obj.min_duration,
            max_duration=filter_obj.max_duration,
            include_items_without_interactions=filter_obj.include_items_without_interactions,
            include_recommended_items=filter_obj.include_recommended_items,
            include_discouraged_items=filter_obj.include_discouraged_items,
            include_viewed_items=filter_obj.include_viewed_items,
            include_hidden_items=filter_obj.include_hidden_items,
            created_at=filter_obj.created_at,
            updated_at=filter_obj.updated_at,
        )

    def to_domain(self) -> UserFilter:
        return UserFilter(
            user_id=self.user_id,
            text_filter=self.text_filter,
            min_duration=self.min_duration,
            max_duration=self.max_duration,
            include_items_without_interactions=self.include_items_without_interactions,
            include_recommended_items=self.include_recommended_items,
            include_discouraged_items=self.include_discouraged_items,
            include_viewed_items=self.include_viewed_items,
            include_hidden_items=self.include_hidden_items,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class MongoDBUserFilterRepository(UserFilterRepository):
    _collection_name: str = "user_filters"

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

    async def get(self, user_id: UUID) -> UserFilter | None:
        result = await self._collection().find_one({"user_id": user_id})
        if result is None:
            return None
        result.pop("_id", None)
        return MongoDBUserFilter(**result).to_domain()

    async def upsert(self, user_filter: UserFilter) -> None:
        user_filter.updated_at = datetime.now(timezone.utc)
        await self._collection().update_one(
            {"user_id": user_filter.user_id},
            {"$set": MongoDBUserFilter.from_domain(user_filter).model_dump()},
            upsert=True,
        )

    async def delete(self, user_id: UUID) -> None:
        await self._collection().delete_one({"user_id": user_id})

    async def delete_all(self) -> None:
        await self._collection().delete_many({})
