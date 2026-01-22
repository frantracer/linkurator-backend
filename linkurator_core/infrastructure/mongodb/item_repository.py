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
from linkurator_core.infrastructure.mongodb.common import (
    MongoDBMapping,
    extract_keywords_from_text,
    normalize_text_search,
)
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
    provider: ItemProvider
    deleted_at: datetime | None = None
    duration: Seconds | None = None
    version: int = 0

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
            provider=item.provider,
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
            provider=self.provider,
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
        filter_query["provider"] = criteria.provider
    if criteria.text is not None and len(criteria.text) > 0:
        keywords = extract_keywords_from_text(criteria.text)
        filter_query["$text"] = {"$search": normalize_text_search(" ".join(keywords))}
    if criteria.max_duration is not None and criteria.min_duration is not None:
        filter_query["duration"] = {"$gte": criteria.min_duration, "$lte": criteria.max_duration}
    elif criteria.max_duration is not None:
        filter_query["$or"] = [
            {"duration": None},
            {"duration": {"$lte": criteria.max_duration}},
        ]
    elif criteria.min_duration is not None:
        filter_query["$or"] = [
            {"duration": None},
            {"duration": {"$gte": criteria.min_duration}},
        ]

    return filter_query


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
        count_pipeline: list[dict[str, Any]] = [
            {"$match": _generate_filter_query(criteria)},
            {"$count": "total"},
        ]
        item_collection = self._item_collection()
        count_result = await item_collection.aggregate(count_pipeline).to_list(length=1)
        total = count_result[0]["total"] if len(count_result) > 0 else 0

        if total == 0 or page_number * limit >= total:
            return []

        if total > 1_000 and criteria.interactions_from_user is not None and not criteria.interactions.without_interactions:
            return await self._find_items_right_join_interactions(criteria, page_number, limit)
        return await self._find_items_left_join_interactions(criteria, page_number, limit)

    async def _find_items_left_join_interactions(
            self, criteria: ItemFilterCriteria, page_number: int, limit: int,
    ) -> list[Item]:
        pipeline: list[dict[str, Any]] = [
            {"$match": _generate_filter_query(criteria)},
            {"$sort": {"published_at": -1}},
        ]

        if criteria.interactions_from_user is not None:
            or_conditions: list[dict[str, Any]] = []
            if criteria.interactions.recommended:
                or_conditions.append({"user_interactions": {"$in": [InteractionType.RECOMMENDED.value]}})
            if criteria.interactions.discouraged:
                or_conditions.append({"user_interactions": {"$in": [InteractionType.DISCOURAGED.value]}})
            if criteria.interactions.viewed:
                or_conditions.append({"user_interactions": {"$in": [InteractionType.VIEWED.value]}})
            if criteria.interactions.hidden:
                or_conditions.append({"user_interactions": {"$in": [InteractionType.HIDDEN.value]}})
            if criteria.interactions.without_interactions:
                or_conditions.append({"user_interactions": {"$size": 0}})

            pipeline.extend([
                {
                    "$lookup": {
                        "from": INTERACTION_COLLECTION_NAME,
                        "let": {"item_uuid": "$uuid"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$item_uuid", "$$item_uuid"]},
                                            {"$eq": ["$user_uuid", criteria.interactions_from_user]},
                                        ],
                                    },
                                },
                            },
                        ],
                        "as": "user_interactions",
                    },
                },
                {
                    "$set": {
                        "user_interactions": {
                            "$map": {
                                "input": "$user_interactions",
                                "as": "interaction",
                                "in": "$$interaction.type",
                            },
                        },
                    },
                },
                {
                    "$match": {
                        "$or": or_conditions,
                    },
                },
            ])

        pipeline.extend([
            {"$skip": page_number * limit},
            {"$limit": limit},
        ])

        item_collection = self._item_collection()
        items_result = await item_collection.aggregate(pipeline).to_list(length=None)

        return [MongoDBItem(**item).to_domain_item() for item in items_result]

    async def _find_items_right_join_interactions(
            self, criteria: ItemFilterCriteria, page_number: int, limit: int,
    ) -> list[Item]:
        # Build interaction match conditions
        interaction_match_conditions: list[dict[str, Any]] = []

        if criteria.interactions.recommended:
            interaction_match_conditions.append({"type": InteractionType.RECOMMENDED.value})
        if criteria.interactions.discouraged:
            interaction_match_conditions.append({"type": InteractionType.DISCOURAGED.value})
        if criteria.interactions.viewed:
            interaction_match_conditions.append({"type": InteractionType.VIEWED.value})
        if criteria.interactions.hidden:
            interaction_match_conditions.append({"type": InteractionType.HIDDEN.value})

        # Start pipeline from interactions collection
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "user_uuid": criteria.interactions_from_user,
                    "$or": interaction_match_conditions if interaction_match_conditions else [{}],
                },
            },
            {
                "$group": {
                    "_id": "$item_uuid",
                    "interaction_types": {"$push": "$type"},
                    "latest_interaction": {"$max": "$created_at"},
                },
            },
            {
                "$lookup": {
                    "from": ITEM_COLLECTION_NAME,
                    "localField": "_id",
                    "foreignField": "uuid",
                    "as": "item",
                },
            },
            {
                "$unwind": "$item",
            },
        ]

        # Apply item-level filters
        item_filter_conditions = _generate_filter_query(criteria)
        if item_filter_conditions:
            # Prefix all conditions with "item." to match the structure after lookup
            prefixed_conditions = {}
            for key, value in item_filter_conditions.items():
                prefixed_conditions[f"item.{key}"] = value

            pipeline.append({
                "$match": prefixed_conditions,
            })

        # Add sorting and pagination
        pipeline.extend([
            {"$sort": {"item.published_at": -1}},
            {"$skip": page_number * limit},
            {"$limit": limit},
            {
                "$replaceRoot": {"newRoot": "$item"},
            },
        ])

        interaction_collection = self._interaction_collection()
        items_result = await interaction_collection.aggregate(pipeline).to_list(length=None)

        return [MongoDBItem(**item).to_domain_item() for item in items_result]

    async def _find_items_without_user_interactions(
            self, criteria: ItemFilterCriteria, page_number: int, limit: int,
    ) -> list[Item]:
        """Find items that have no interactions from the specified user"""
        # Get all item UUIDs that have interactions from this user
        interaction_collection = self._interaction_collection()
        items_with_interactions = await interaction_collection.distinct(
            "item_uuid",
            {"user_uuid": criteria.interactions_from_user},
        )

        # Build item filter excluding items with interactions
        item_filter = _generate_filter_query(criteria)
        if items_with_interactions:
            item_filter["uuid"] = {"$nin": items_with_interactions}

        # Find items without interactions
        pipeline: list[dict[str, Any]] = [
            {"$match": item_filter},
            {"$sort": {"published_at": -1}},
            {"$skip": page_number * limit},
            {"$limit": limit},
        ]

        item_collection = self._item_collection()
        items_result = await item_collection.aggregate(pipeline).to_list(length=None)

        return [MongoDBItem(**item).to_domain_item() for item in items_result]

    async def _get_items_from_interactions_pipeline(
            self, pipeline: list[dict[str, Any]], page_number: int, limit: int,
    ) -> list[Item]:
        """Execute the interactions-based pipeline and return items"""
        # Add sorting and pagination
        pipeline.extend([
            {"$sort": {"item.published_at": -1}},
            {"$skip": page_number * limit},
            {"$limit": limit},
            {
                "$replaceRoot": {"newRoot": "$item"},
            },
        ])

        interaction_collection = self._interaction_collection()
        items_result = await interaction_collection.aggregate(pipeline).to_list(length=None)

        return [MongoDBItem(**item).to_domain_item() for item in items_result]

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

    async def count_items(self, provider: ItemProvider | None = None) -> int:
        collection = self._item_collection()
        query: dict[str, Any] = {"deleted_at": None}
        if provider is not None:
            query["provider"] = provider

        # Use aggregation pipeline with index hint for better performance
        pipeline: list[dict[str, Any]] = [
            {"$match": query},
            {"$count": "total"},
        ]

        result = await collection.aggregate(pipeline).to_list(length=1)
        return result[0]["total"] if result else 0

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
