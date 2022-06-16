from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import AnyUrl
from pydantic.main import BaseModel
import pymongo  # type: ignore
from pymongo import MongoClient

from linkurator_core.domain.subscription import Subscription
from linkurator_core.domain.subscription_repository import SubscriptionRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBSubscription(BaseModel):
    uuid: UUID
    name: str
    provider: str
    external_data: Dict[str, str]
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime

    @staticmethod
    def from_domain_subscription(subscription: Subscription) -> MongoDBSubscription:
        return MongoDBSubscription(
            uuid=subscription.uuid,
            name=subscription.name,
            provider=subscription.provider,
            external_data=subscription.external_data,
            url=subscription.url,
            thumbnail=subscription.thumbnail,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            scanned_at=subscription.scanned_at
        )

    def to_domain_subscription(self) -> Subscription:
        return Subscription(
            uuid=self.uuid,
            name=self.name,
            provider=self.provider,
            external_data=self.external_data,
            url=self.url,
            thumbnail=self.thumbnail,
            created_at=self.created_at,
            updated_at=self.updated_at,
            scanned_at=self.scanned_at
        )


class MongoDBSubscriptionRepository(SubscriptionRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'subscriptions'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password,
                                  uuidRepresentation='standard')
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, subscription: Subscription):
        collection = self._subscription_collection()
        collection.insert_one(dict(MongoDBSubscription.from_domain_subscription(subscription)))

    def get(self, subscription_id: UUID) -> Optional[Subscription]:
        collection = self._subscription_collection()
        subscription: Optional[Dict] = collection.find_one({'uuid': subscription_id})
        if subscription is None:
            return None
        return MongoDBSubscription(**subscription).to_domain_subscription()

    def get_list(self, subscription_ids: List[UUID]) -> List[Subscription]:
        collection = self._subscription_collection()
        subscriptions: List[Dict] = list(collection.
                                         find({'uuid': {'$in': subscription_ids}}).
                                         sort('created_at', pymongo.DESCENDING))
        return [MongoDBSubscription(**subscription).to_domain_subscription() for subscription in subscriptions]

    def delete(self, subscription_id: UUID):
        collection = self._subscription_collection()
        collection.delete_one({'uuid': subscription_id})

    def find(self, subscription: Subscription) -> Optional[Subscription]:
        collection = self._subscription_collection()
        found_subscription: Optional[Dict] = collection.find_one({'url': subscription.url})
        if found_subscription is None:
            return None
        return MongoDBSubscription(**found_subscription).to_domain_subscription()

    def _subscription_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name][self._collection_name]
