from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel

from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUser


class MongoDBRegistrationRequest(BaseModel):
    uuid: UUID
    user: MongoDBUser
    valid_until: datetime

    @staticmethod
    def from_domain_registration_request(request: RegistrationRequest) -> MongoDBRegistrationRequest:
        return MongoDBRegistrationRequest(
            uuid=request.uuid,
            user=MongoDBUser.from_domain_user(request.user),
            valid_until=request.valid_until
        )

    def to_domain_registration_request(self) -> RegistrationRequest:
        return RegistrationRequest(
            uuid=self.uuid,
            user=self.user.to_domain_user(),
            valid_until=self.valid_until
        )


class MongoDBRegistrationRequestRepository(RegistrationRequestRepository):
    _collection_name = 'registration_requests'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self.client = AsyncIOMotorClient[MongoDBMapping](
            f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

    def _collection(self) -> AsyncIOMotorCollection[MongoDBMapping]:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name, codec_options=codec_options).get_collection(self._collection_name)

    async def check_connection(self) -> None:
        if self._collection_name not in await self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    async def add_request(self, request: RegistrationRequest) -> None:
        await self._collection().insert_one(
            MongoDBRegistrationRequest.from_domain_registration_request(request).model_dump()
        )

    async def get_request(self, uuid: UUID) -> RegistrationRequest | None:
        request = await self._collection().find_one({'uuid': uuid})
        return MongoDBRegistrationRequest(**request).to_domain_registration_request() if request else None

    async def delete_request(self, uuid: UUID) -> None:
        await self._collection().delete_one({'uuid': uuid})
