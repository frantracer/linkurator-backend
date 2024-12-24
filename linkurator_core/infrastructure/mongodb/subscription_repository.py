from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Dict, List, Optional, Any
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import AnyUrl
from pydantic.main import BaseModel
from pymongo import DESCENDING

from linkurator_core.domain.common import utils
from linkurator_core.domain.subscriptions.subscription import (
    Subscription,
    SubscriptionProvider,
)
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionRepository,
)
from linkurator_core.infrastructure.mongodb.common import normalize_text_search
from linkurator_core.infrastructure.mongodb.repositories import (
    CollectionIsNotInitialized,
)


class MongoDBSubscription(BaseModel):
    uuid: UUID
    name: str
    provider: str
    external_data: Dict[str, str]
    url: str
    thumbnail: str
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime
    last_published_at: datetime = datetime.fromtimestamp(0, tz=timezone.utc)

    @staticmethod
    def from_domain_subscription(subscription: Subscription) -> MongoDBSubscription:
        return MongoDBSubscription(
            uuid=subscription.uuid,
            name=subscription.name,
            provider=subscription.provider.value,
            external_data=subscription.external_data,
            url=str(subscription.url),
            thumbnail=str(subscription.thumbnail),
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            scanned_at=subscription.scanned_at,
            last_published_at=subscription.last_published_at,
        )

    def to_domain_subscription(self) -> Subscription:
        return Subscription(
            uuid=self.uuid,
            name=self.name,
            provider=SubscriptionProvider(self.provider),
            external_data=self.external_data,
            url=utils.parse_url(self.url),
            thumbnail=utils.parse_url(self.thumbnail),
            created_at=self.created_at,
            updated_at=self.updated_at,
            scanned_at=self.scanned_at,
            last_published_at=self.last_published_at,
        )


class MongoDBSubscriptionRepository(SubscriptionRepository):
    client: AsyncIOMotorClient[Any]
    db_name: str
    _collection_name: str = "subscriptions"

    def __init__(
        self, ip: IPv4Address, port: int, db_name: str, username: str, password: str
    ) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient(
            f"mongodb://{str(ip)}:{port}/", username=username, password=password
        )
        self.db_name = db_name

    async def check_connection(self) -> None:
        if (
            self._collection_name
            not in await self.client[self.db_name].list_collection_names()
        ):
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'"
            )

    async def add(self, subscription: Subscription) -> None:
        collection = await self._subscription_collection()
        await collection.insert_one(
            MongoDBSubscription.from_domain_subscription(subscription).model_dump()
        )

    async def get(self, subscription_id: UUID) -> Optional[Subscription]:
        collection = await self._subscription_collection()
        subscription: Optional[dict[str, Any]] = await collection.find_one(
            {"uuid": subscription_id}
        )
        if subscription is None:
            return None
        return MongoDBSubscription(**subscription).to_domain_subscription()

    async def get_list(self, subscription_ids: List[UUID]) -> List[Subscription]:
        collection = await self._subscription_collection()
        subscriptions: List[dict[str, Any]] = (
            await collection.find({"uuid": {"$in": subscription_ids}})
            .sort("created_at", DESCENDING)
            .to_list(length=None)
        )
        return [
            MongoDBSubscription(**subscription).to_domain_subscription()
            for subscription in subscriptions
        ]

    async def delete(self, subscription_id: UUID) -> None:
        collection = await self._subscription_collection()
        await collection.delete_one({"uuid": subscription_id})

    async def delete_all(self) -> None:
        collection = await self._subscription_collection()
        await collection.delete_many({})

    async def update(self, subscription: Subscription) -> None:
        collection = await self._subscription_collection()
        await collection.update_one(
            {"uuid": subscription.uuid},
            {
                "$set": MongoDBSubscription.from_domain_subscription(
                    subscription
                ).model_dump()
            },
        )

    async def find_by_url(self, url: AnyUrl) -> Optional[Subscription]:
        collection = await self._subscription_collection()
        found_subscription: Optional[dict[str, Any]] = await collection.find_one(
            {"url": str(url)}
        )
        if found_subscription is None:
            return None
        return MongoDBSubscription(**found_subscription).to_domain_subscription()

    async def find_latest_scan_before(
        self, datetime_limit: datetime
    ) -> List[Subscription]:
        collection = await self._subscription_collection()
        subscriptions: List[dict[str, Any]] = await (
            collection.find({"scanned_at": {"$lt": datetime_limit}})
            .sort("scanned_at", DESCENDING)
            .to_list(length=None)
        )
        return [
            MongoDBSubscription(**subscription).to_domain_subscription()
            for subscription in subscriptions
        ]

    async def find_by_name(self, name: str) -> List[Subscription]:
        collection = await self._subscription_collection()

        subscriptions: List[dict[str, Any]] = await (
            collection.find({"$text": {"$search": normalize_text_search(name)}})
            .sort("created_at", DESCENDING)
            .to_list(length=None)
        )
        return [
            MongoDBSubscription(**subscription).to_domain_subscription()
            for subscription in subscriptions
        ]

    async def _subscription_collection(self) -> AsyncIOMotorCollection[Any]:
        codec_options = CodecOptions(
            tz_aware=True, uuid_representation=UuidRepresentation.STANDARD
        )  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            self._collection_name, codec_options=codec_options
        )

    async def count_subscriptions(
        self, provider: Optional[SubscriptionProvider] = None
    ) -> int:
        collection = await self._subscription_collection()
        query = {} if provider is None else {"provider": provider.value}
        return await collection.count_documents(query)
