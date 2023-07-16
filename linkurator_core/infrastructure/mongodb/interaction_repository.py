from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Dict, List, Optional
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
import pymongo  # type: ignore
from pydantic import BaseModel
from pymongo import MongoClient

from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.interaction_repository import InteractionRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


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
            created_at=interaction.created_at
        )

    def to_domain_interaction(self) -> Interaction:
        return Interaction(
            uuid=self.uuid,
            item_uuid=self.item_uuid,
            user_uuid=self.user_uuid,
            type=self.type,
            created_at=self.created_at
        )


class MongoDBInteractionRepository(InteractionRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'interactions'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, interaction: Interaction):
        collection = self._interaction_collection()
        collection.insert_one(dict(MongoDBInteraction.from_domain_interaction(interaction)))

    def delete(self, interaction_id: UUID):
        collection = self._interaction_collection()
        collection.delete_one({'uuid': interaction_id})

    def get(self, interaction_id: UUID) -> Optional[Interaction]:
        collection = self._interaction_collection()
        interaction = collection.find_one({'uuid': interaction_id})
        if interaction is None:
            return None
        return MongoDBInteraction(**interaction).to_domain_interaction()

    def get_user_interactions_by_item_id(self, user_id: UUID, item_ids: List[UUID]) -> Dict[UUID, List[Interaction]]:
        collection = self._interaction_collection()
        interactions = collection.find({'user_uuid': user_id, 'item_uuid': {'$in': item_ids}})
        result: Dict[UUID, List[Interaction]] = {}
        for interaction in interactions:
            if interaction['item_uuid'] not in result:
                result[interaction['item_uuid']] = []
            result[interaction['item_uuid']].append(MongoDBInteraction(**interaction).to_domain_interaction())
        for item_id in item_ids:
            if item_id not in result:
                result[item_id] = []
        return result

    def _interaction_collection(self) -> pymongo.collection.Collection:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            self._collection_name,
            codec_options=codec_options)
