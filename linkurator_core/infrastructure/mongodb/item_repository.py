from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Dict, List, Optional, Any
from uuid import UUID

import pymongo  # type: ignore
from pydantic import AnyUrl
from pydantic.main import BaseModel
from pymongo import MongoClient
from pymongo.cursor import Cursor

from linkurator_core.domain.item import Item
from linkurator_core.domain.item_repository import ItemRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBItem(BaseModel):
    uuid: UUID
    subscription_uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain_item(item: Item) -> MongoDBItem:
        return MongoDBItem(
            uuid=item.uuid,
            subscription_uuid=item.subscription_uuid,
            name=item.name,
            url=item.url,
            thumbnail=item.thumbnail,
            created_at=item.created_at,
            updated_at=item.updated_at
        )

    def to_domain_item(self) -> Item:
        return Item(
            uuid=self.uuid,
            subscription_uuid=self.subscription_uuid,
            name=self.name,
            url=self.url,
            thumbnail=self.thumbnail,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class MongoDBItemRepository(ItemRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'items'

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, item: Item):
        collection = self._item_collection()
        collection.insert_one(dict(MongoDBItem.from_domain_item(item)))

    def get(self, item_id: UUID) -> Optional[Item]:
        collection = self._item_collection()
        item: Optional[Dict] = collection.find_one({'uuid': item_id})
        if item is None:
            return None
        return MongoDBItem(**item).to_domain_item()

    def delete(self, item_id: UUID):
        collection = self._item_collection()
        collection.delete_one({'uuid': item_id})

    def get_by_subscription_id(self, subscription_id: UUID) -> List[Item]:
        collection = self._item_collection()
        items: Cursor[Any] = collection.find({'subscription_uuid': subscription_id}) \
            .sort('created_at', pymongo.DESCENDING)
        return [MongoDBItem(**item).to_domain_item() for item in items]

    def _item_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name][self._collection_name]
