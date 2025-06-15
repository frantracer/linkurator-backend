from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.domain.users.password_change_request_repository import PasswordChangeRequestRepository
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBPasswordChangeRequest(BaseModel):
    uuid: UUID
    user_id: UUID
    valid_until: int
    validation_base_url: str

    @staticmethod
    def from_domain_password_change_request(request: PasswordChangeRequest) -> MongoDBPasswordChangeRequest:
        return MongoDBPasswordChangeRequest(
            uuid=request.uuid,
            user_id=request.user_id,
            valid_until=int(request.valid_until.timestamp()),
            validation_base_url=str(request.validation_base_url),
        )

    def to_domain_password_change_request(self) -> PasswordChangeRequest:
        return PasswordChangeRequest(
            uuid=self.uuid,
            user_id=self.user_id,
            valid_until=datetime.fromtimestamp(self.valid_until, tz=timezone.utc),
            validation_base_url=AnyUrl(self.validation_base_url),
        )


class MongoDBPasswordChangeRequestRepository(PasswordChangeRequestRepository):
    _collection_name = "password_change_requests"

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
            msg = f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'"
            raise CollectionIsNotInitialized(
                msg)

    async def add_request(self, request: PasswordChangeRequest) -> None:
        await self._collection().insert_one(
            MongoDBPasswordChangeRequest.from_domain_password_change_request(request).model_dump())

    async def get_request(self, uuid: UUID) -> PasswordChangeRequest | None:
        document = await self._collection().find_one({"uuid": uuid})
        return MongoDBPasswordChangeRequest(**document).to_domain_password_change_request() if document else None

    async def delete_request(self, uuid: UUID) -> None:
        await self._collection().delete_one({"uuid": uuid})
