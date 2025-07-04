from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

import pymongo
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic.main import BaseModel

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import InteractionFilterCriteria, ItemFilterCriteria, ItemRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping, normalize_text_search
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized

ITEM_COLLECTION_NAME = "items"
INTERACTION_COLLECTION_NAME = "interactions"


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
    deleted_at: datetime | None = None
    duration: Seconds | None = None
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
            deleted_at=item.deleted_at,
            published_at=item.published_at,
            provider=item.provider.value,
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
            deleted_at=self.deleted_at,
            published_at=self.published_at,
            provider=ItemProvider(self.provider),
        )


class MongoDBInteraction(BaseModel):
    uuid: UUID
    item_uuid: UUID
    user_uuid: UUID
    type: InteractionType
    created_at: datetime

    @staticmethod
    def from_domain_interaction(interaction: Interaction) -> MongoDBInteraction:
        return MongoDBInteraction(
            uuid=interaction.uuid,
            item_uuid=interaction.item_uuid,
            user_uuid=interaction.user_uuid,
            type=interaction.type,
            created_at=interaction.created_at,
        )

    def to_domain_interaction(self) -> Interaction:
        return Interaction(
            uuid=self.uuid,
            item_uuid=self.item_uuid,
            user_uuid=self.user_uuid,
            type=self.type,
            created_at=self.created_at,
        )


def _generate_filter_query(criteria: ItemFilterCriteria) -> dict[str, Any]:
    filter_query: dict[str, Any] = {
        "deleted_at": None,
    }
    if criteria.item_ids is not None:
        filter_query["uuid"] = {"$in": list(criteria.item_ids)}
    if criteria.subscription_ids is not None:
        filter_query["subscription_uuid"] = {"$in": criteria.subscription_ids}
    if criteria.published_after is not None:
        filter_query["published_at"] = {"$gt": criteria.published_after}
    if criteria.created_before is not None:
        filter_query["created_at"] = {"$lt": criteria.created_before}
    if criteria.updated_before is not None:
        filter_query["updated_at"] = {"$lt": criteria.updated_before}
    if criteria.url is not None:
        filter_query["url"] = str(criteria.url)
    if criteria.last_version is not None:
        filter_query["version"] = {"$lt": criteria.last_version}
    if criteria.provider is not None:
        filter_query["provider"] = criteria.provider.value
    if criteria.text is not None and len(criteria.text) > 0:
        filter_query["$text"] = {"$search": normalize_text_search(criteria.text)}

    if criteria.max_duration is not None and criteria.min_duration is not None:
        filter_query["duration"] = {"$gte": criteria.min_duration, "$lte": criteria.max_duration}
    elif criteria.max_duration is not None:
        filter_query["duration"] = {"$lte": criteria.max_duration}
    elif criteria.min_duration is not None:
        filter_query["duration"] = {"$gte": criteria.min_duration}

    return filter_query


def _generate_filter_interaction_query(criteria: ItemFilterCriteria) -> dict[str, Any]:
    interaction_filter: list[dict[str, Any]] = []
    if criteria.interactions.recommended or criteria.interactions.without_interactions:
        interaction_filter = [*interaction_filter, {"type": InteractionType.RECOMMENDED.value}]
    if criteria.interactions.discouraged or criteria.interactions.without_interactions:
        interaction_filter = [*interaction_filter, {"type": InteractionType.DISCOURAGED.value}]
    if criteria.interactions.viewed or criteria.interactions.without_interactions:
        interaction_filter = [*interaction_filter, {"type": InteractionType.VIEWED.value}]
    if criteria.interactions.hidden or criteria.interactions.without_interactions:
        interaction_filter = [*interaction_filter, {"type": InteractionType.HIDDEN.value}]

    filter_interactions_query: dict[str, Any] = {
        "user_uuid": criteria.interactions_from_user,
    }
    if len(interaction_filter) > 0:
        filter_interactions_query["$or"] = interaction_filter

    return filter_interactions_query


class MongoDBItemRepository(ItemRepository):
    db_name: str

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient[MongoDBMapping](
            f"mongodb://{ip!s}:{port}/", username=username, password=password)
        self.db_name = db_name

    async def check_connection(self) -> None:
        for collection_name in [ITEM_COLLECTION_NAME, INTERACTION_COLLECTION_NAME]:
            if collection_name not in await self.client[self.db_name].list_collection_names():
                msg = f"Collection '{collection_name}' is not initialized in database '{self.db_name}'"
                raise CollectionIsNotInitialized(
                    msg)

    async def upsert_items(self, items: list[Item]) -> None:
        if len(items) == 0:
            return
        collection = self._item_collection()
        await collection.bulk_write([
            pymongo.ReplaceOne(
                {"uuid": item.uuid},
                MongoDBItem.from_domain_item(item).model_dump(),
                upsert=True,
            ) for item in items
        ])

    async def get_item(self, item_id: UUID) -> Item | None:
        collection = self._item_collection()
        item: dict[str, Any] | None = await collection.find_one({"uuid": item_id})
        if item is None:
            return None
        mongo_item = MongoDBItem(**item)
        if mongo_item.deleted_at is not None:
            return None
        return mongo_item.to_domain_item()

    async def delete_item(self, item_id: UUID) -> None:
        collection = self._item_collection()
        await collection.update_one(
            {"uuid": item_id},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}},
        )

    async def find_items(self, criteria: ItemFilterCriteria, page_number: int, limit: int) -> list[Item]:
        items: list[Item] = []

        filter_with_interactions: bool = False
        interactions_by_item: dict[UUID, list[InteractionType]] = {}

        if criteria.interactions_from_user is not None:
            filter_with_interactions = True
            interaction_collection = self._interaction_collection()
            interaction_results = list(await interaction_collection.aggregate([
                {
                    "$match": _generate_filter_interaction_query(criteria),
                },
                {
                    "$group": {
                        "_id": "$item_uuid",
                        "values": {"$push": "$$ROOT.type"},
                    },
                },
            ]).to_list(length=None))

            for result in interaction_results:
                interactions_by_item[result["_id"]] = result["values"]

        more_items = True
        internal_page_size = 100
        internal_page_number = 0
        while len(items) < (page_number + 1) * limit and more_items:
            item_collection = self._item_collection()
            items_result = list(await item_collection.aggregate([
                {"$match": _generate_filter_query(criteria)},
                {"$sort": {"published_at": -1}},
                {"$skip": internal_page_number * internal_page_size},
                {"$limit": internal_page_size},
            ]).to_list(length=None))

            if len(items_result) == 0:
                more_items = False

            if filter_with_interactions:
                items = items + self._filter_items_with_interactions(items_result, criteria, interactions_by_item)
            else:
                items = items + [MongoDBItem(**item).to_domain_item() for item in items_result]

            if filter_with_interactions and len(interactions_by_item) == len(items):
                more_items = False

            internal_page_number = internal_page_number + 1

        return items[page_number * limit: min((page_number + 1) * limit, len(items))]

    @staticmethod
    def _filter_items_with_interactions(
            items_result: list[dict[str, Any]],
            criteria: ItemFilterCriteria,
            interactions_by_item: dict[UUID, list[InteractionType]],
    ) -> list[Item]:
        items = []
        for item in items_result:
            interactions = interactions_by_item.get(item["uuid"], [])
            if interactions is not None:
                add_item = False
                if (criteria.interactions.recommended and InteractionType.RECOMMENDED.value in interactions) or (criteria.interactions.discouraged and InteractionType.DISCOURAGED.value in interactions) or ((criteria.interactions.viewed and InteractionType.VIEWED.value in interactions) or (criteria.interactions.hidden and InteractionType.HIDDEN.value in interactions)) or (len(interactions) == 0 and criteria.interactions.without_interactions is True):
                    add_item = True

                if add_item is True:
                    items.append(MongoDBItem(**item).to_domain_item())

        return items

    async def delete_all_items(self) -> None:
        collection = self._item_collection()
        await collection.update_many(
            {},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}},
        )

    async def add_interaction(self, interaction: Interaction) -> None:
        collection = self._interaction_collection()
        await collection.insert_one(dict(MongoDBInteraction.from_domain_interaction(interaction)))

    async def delete_interaction(self, interaction_id: UUID) -> None:
        collection = self._interaction_collection()
        await collection.delete_one({"uuid": interaction_id})

    async def get_interaction(self, interaction_id: UUID) -> Interaction | None:
        collection = self._interaction_collection()
        interaction = await collection.find_one({"uuid": interaction_id})
        if interaction is None:
            return None
        return MongoDBInteraction(**interaction).to_domain_interaction()

    async def get_user_interactions_by_item_id(
            self, user_id: UUID, item_ids: list[UUID],
    ) -> dict[UUID, list[Interaction]]:
        collection = self._interaction_collection()
        interactions = await collection.find(
            {
                "user_uuid": user_id,
                "item_uuid": {"$in": item_ids},
            },
        ).to_list(length=None)
        result: dict[UUID, list[Interaction]] = {}
        for interaction in interactions:
            if interaction["item_uuid"] not in result:
                result[interaction["item_uuid"]] = []
            result[interaction["item_uuid"]].append(MongoDBInteraction(**interaction).to_domain_interaction())
        for item_id in item_ids:
            if item_id not in result:
                result[item_id] = []
        return result

    async def find_interactions(
            self, criteria: InteractionFilterCriteria, page_number: int, limit: int,
    ) -> list[Interaction]:
        interactions_filter: dict[str, Any] = {}

        and_filters: list[Any] = []

        if criteria.item_ids is not None:
            and_filters.append({"$or": [{"item_uuid": item_id} for item_id in criteria.item_ids]})

        if criteria.user_ids is not None:
            and_filters.append({"$or": [{"user_uuid": user_id} for user_id in criteria.user_ids]})

        if criteria.interaction_types is not None:
            and_filters.append(
                {"$or": [{"type": interaction_type.value} for interaction_type in criteria.interaction_types]},
            )

        if len(and_filters) > 0:
            interactions_filter["$and"] = and_filters

        if criteria.created_before is not None:
            interactions_filter["created_at"] = {"$lt": criteria.created_before}

        pipeline: list[Any] = [
            {"$match": interactions_filter},
            {"$sort": {"created_at": -1}},
        ]

        interactions_collection = self._interaction_collection()
        interactions = await interactions_collection.aggregate(pipeline).to_list(length=None)

        if any(value is not None for value in [criteria.text, criteria.min_duration, criteria.max_duration]):
            items_uuids = {interaction["item_uuid"] for interaction in interactions}
            items = await self.find_items(criteria=ItemFilterCriteria(
                item_ids=items_uuids,
                text=criteria.text,
                min_duration=criteria.min_duration,
                max_duration=criteria.max_duration),
                page_number=0,
                limit=len(items_uuids),
            )
            filtered_items_uuids = {item.uuid for item in items}
            interactions = [interaction
                            for interaction in interactions
                            if interaction["item_uuid"] in filtered_items_uuids]

        first_index = page_number * limit
        last_index = (page_number + 1) * limit
        interactions = interactions[first_index:last_index]

        return [MongoDBInteraction(**interaction).to_domain_interaction() for interaction in interactions]

    async def delete_all_interactions(self) -> None:
        collection = self._interaction_collection()
        await collection.delete_many({})

    def _item_collection(self) -> Any:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            name=ITEM_COLLECTION_NAME,
            codec_options=codec_options)

    def _interaction_collection(self) -> Any:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            name=INTERACTION_COLLECTION_NAME,
            codec_options=codec_options)
