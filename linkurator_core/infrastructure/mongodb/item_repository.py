from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, Dict, List, Optional
from uuid import UUID

import pymongo  # type: ignore
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from pydantic.main import BaseModel
from pymongo import MongoClient
from pymongo.cursor import Cursor

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria, FindResult
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBItem(BaseModel):
    uuid: UUID
    subscription_uuid: UUID
    name: str
    description: str
    url: str
    thumbnail: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime
    deleted_at: Optional[datetime] = None
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
            url=str(item.url),
            thumbnail=str(item.thumbnail),
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
            url=utils.parse_url(self.url),
            thumbnail=utils.parse_url(self.thumbnail),
            duration=self.duration,
            version=self.version,
            created_at=self.created_at,
            updated_at=self.updated_at,
            published_at=self.published_at,
            provider=ItemProvider(self.provider)
        )


class MongoDBItemRepository(ItemRepository):
    client: MongoClient[Any]
    db_name: str
    _collection_name: str = 'items'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def upsert_bulk(self, items: List[Item]):
        if len(items) == 0:
            return
        collection = self._item_collection()
        collection.bulk_write([
            pymongo.ReplaceOne(
                {'uuid': item.uuid},
                MongoDBItem.from_domain_item(item).model_dump(),
                upsert=True
            ) for item in items
        ])

    def get(self, item_id: UUID) -> Optional[Item]:
        collection = self._item_collection()
        item: Optional[dict[str, Any]] = collection.find_one({'uuid': item_id})
        if item is None:
            return None
        mongo_item = MongoDBItem(**item)
        if mongo_item.deleted_at is not None:
            return None
        return mongo_item.to_domain_item()

    def delete(self, item_id: UUID) -> None:
        collection = self._item_collection()
        collection.update_one(
            {'uuid': item_id},
            {'$set': {'deleted_at': datetime.utcnow()}}
        )

    def find_items(self, criteria: ItemFilterCriteria, page_number: int, limit: int) -> FindResult:
        filter_query: Dict[str, Any] = {
            'deleted_at': None
        }
        if criteria.item_ids is not None:
            filter_query['uuid'] = {'$in': list(criteria.item_ids)}
        if criteria.subscription_ids is not None:
            filter_query['subscription_uuid'] = {'$in': criteria.subscription_ids}
        if criteria.published_after:
            filter_query['published_at'] = {'$gt': criteria.published_after}
        if criteria.created_before:
            filter_query['created_at'] = {'$lt': criteria.created_before}
        if criteria.url:
            filter_query['url'] = str(criteria.url)
        if criteria.last_version:
            filter_query['version'] = {'$lt': criteria.last_version}
        if criteria.provider:
            filter_query['provider'] = criteria.provider.value
        if criteria.text:
            filter_query['$text'] = {'$search': criteria.text}

        collection = self._item_collection()
        total_items: int = collection.count_documents(filter_query)

        items: Cursor[Any] = collection.find(filter_query).sort(
            'published_at', pymongo.DESCENDING
        ).skip(
            page_number * limit
        ).limit(
            limit
        )

        return [MongoDBItem(**item).to_domain_item() for item in items], total_items

    def delete_all_items(self) -> None:
        collection = self._item_collection()
        collection.update_many(
            {},
            {'$set': {'deleted_at': datetime.utcnow()}}
        )

    def _item_collection(self) -> Any:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            self._collection_name,
            codec_options=codec_options)
