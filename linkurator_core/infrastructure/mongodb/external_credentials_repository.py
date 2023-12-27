from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, List, Optional
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
from pydantic.main import BaseModel

from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBExternalCredentials(BaseModel):
    user_id: UUID
    value: str
    credential_type: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain_credentials(credentials: ExternalServiceCredential) -> MongoDBExternalCredentials:
        return MongoDBExternalCredentials(
            user_id=credentials.user_id,
            credential_type=str(credentials.credential_type.value),
            value=credentials.credential_value,
            created_at=credentials.created_at,
            updated_at=credentials.updated_at
        )

    def to_domain_credentials(self) -> ExternalServiceCredential:
        return ExternalServiceCredential(
            user_id=self.user_id,
            credential_type=ExternalServiceType(self.credential_type),
            credential_value=self.value,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class MongodDBExternalCredentialRepository(ExternalCredentialRepository):
    _collection_name: str = 'external_credentials'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = AsyncIOMotorClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

    def _collection(self) -> Any:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name, codec_options=codec_options).get_collection(self._collection_name)

    async def check_connection(self) -> None:
        if self._collection_name not in await self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    async def get(self, user_id: UUID) -> List[ExternalServiceCredential]:
        return [MongoDBExternalCredentials(**credential).to_domain_credentials()
                for credential in await self._collection().find({'user_id': user_id}).to_list(length=None)]

    async def add(self, credentials: ExternalServiceCredential) -> None:
        await self._collection().insert_one(
            MongoDBExternalCredentials.from_domain_credentials(credentials).model_dump())

    async def update(self, credentials: ExternalServiceCredential) -> None:
        await self._collection().update_one(
            {'user_id': credentials.user_id},
            {'$set': MongoDBExternalCredentials.from_domain_credentials(credentials).model_dump()}
        )

    async def delete(
            self,
            user_id: UUID,
            credential_type: ExternalServiceType,
            credential_value: str
    ) -> None:
        await self._collection().delete_one(
            {'user_id': user_id, 'credential_type': str(credential_type.value), 'value': credential_value}
        )

    async def find_by_users_and_type(
            self,
            user_ids: List[UUID],
            credential_type: ExternalServiceType
    ) -> List[ExternalServiceCredential]:
        return [MongoDBExternalCredentials(**credential).to_domain_credentials()
                for credential in await self._collection().find(
                {'user_id': {'$in': user_ids}, 'credential_type': str(credential_type.value)}
            ).to_list(length=None)]

    async def get_by_value_and_type(
            self,
            credential_type: ExternalServiceType,
            credential_value: str
    ) -> Optional[ExternalServiceCredential]:
        credential = await self._collection().find_one(
            {'credential_type': str(credential_type.value), 'value': credential_value}
        )
        if credential is None:
            return None
        return MongoDBExternalCredentials(**credential).to_domain_credentials()
