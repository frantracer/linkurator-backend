from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import pymongo  # type: ignore
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from pydantic import AnyUrl
from pydantic.main import BaseModel
from pymongo import MongoClient
from pymongo.cursor import Cursor

from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.filter_item_criteria import FilterItemCriteria
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBItem(BaseModel):
    uuid: UUID
    subscription_uuid: UUID
    name: str
    description: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    published_at: datetime
    duration: Optional[Seconds] = None
    version: int = 0
    provider: str = ItemProvider.YOUTUBE.value

    @staticmethod
    def from_domain_item(item: Item) -> MongoDBItem:
        return MongoDBItem(
            uuid=item.uuid,
            subscription_uuid=item.subscription_uuid,
            name=item.name,
            description=item.description,
            url=item.url,
            thumbnail=item.thumbnail,
            duration=item.duration,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at,
            published_at=item.published_at,
            provider=item.provider.value
        )

    def to_domain_item(self) -> Item:
        return Item(
            uuid=self.uuid,
            subscription_uuid=self.subscription_uuid,
            name=self.name,
            description=self.description,
            url=self.url,
            thumbnail=self.thumbnail,
            duration=self.duration,
            version=self.version,
            created_at=self.created_at,
            updated_at=self.updated_at,
            published_at=self.published_at,
            provider=ItemProvider(self.provider)
        )


class MongoDBItemRepository(ItemRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'items'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, item: Item):
        collection = self._item_collection()
        collection.insert_one(dict(MongoDBItem.from_domain_item(item)))

    def add_bulk(self, items: List[Item]):
        if len(items) == 0:
            return
        collection = self._item_collection()
        collection.insert_many([dict(MongoDBItem.from_domain_item(item)) for item in items])

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

    def get_items_created_before(self, date: datetime, limit: int) -> List[Item]:
        if limit <= 0:
            return []
        collection = self._item_collection()
        items: Cursor[Any] = collection.find({'created_at': {'$lt': date}}).limit(limit)
        return [MongoDBItem(**item).to_domain_item() for item in items]

    def find(self, item: Item) -> Optional[Item]:
        collection = self._item_collection()
        db_item: Optional[Dict] = collection.find_one({'url': item.url})
        if db_item is None:
            return None
        return MongoDBItem(**db_item).to_domain_item()

    def find_sorted_by_publish_date(
            self,
            sub_ids: List[UUID],
            published_after: datetime,
            created_before: datetime,
            max_results: int,
            page_number: int,
            criteria: FilterItemCriteria = FilterItemCriteria()
    ) -> Tuple[List[Item], int]:
        collection = self._item_collection()

        filter_query = {
            'subscription_uuid': {'$in': sub_ids},
            'published_at': {'$gt': published_after},
            'created_at': {'$lt': created_before},
        }

        if criteria.text:
            filter_query['$text'] = {'$search': criteria.text}

        total_items: int = collection.count_documents(filter_query)

        items: Cursor[Any] = collection.find(filter_query).sort(
            'published_at', pymongo.DESCENDING
        ).skip(
            page_number * max_results
        ).limit(
            max_results)

        return [MongoDBItem(**item).to_domain_item() for item in items], total_items

    def find_deprecated_items(self, last_version: int, provider: ItemProvider, limit: int) -> List[Item]:
        collection = self._item_collection()
        items: Cursor[Any] = collection.find({
            'version': {'$lt': last_version},
            'provider': provider.value
        }).limit(limit)
        return [MongoDBItem(**item).to_domain_item() for item in items]

    def delete_all_items(self):
        collection = self._item_collection()
        collection.drop()

    def _item_collection(self) -> pymongo.collection.Collection:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            self._collection_name,
            codec_options=codec_options)
