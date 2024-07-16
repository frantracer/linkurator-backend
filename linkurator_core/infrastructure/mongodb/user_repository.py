from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import List, Optional
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from linkurator_core.domain.common import utils
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository, EmailAlreadyInUse
from linkurator_core.infrastructure.mongodb.common import MongoDBMapping
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBUser(BaseModel):
    uuid: UUID
    first_name: str
    last_name: str
    email: str
    locale: str = "en"
    avatar_url: str = 'https://www.linkurator.com/favicon.ico'
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    last_login_at: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    deleted_at: Optional[datetime] = None
    google_refresh_token: Optional[str] = None
    subscription_uuids: List[UUID] = []
    is_admin: bool = False

    @staticmethod
    def from_domain_user(user: User) -> MongoDBUser:
        return MongoDBUser(
            uuid=user.uuid,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            locale=user.locale,
            avatar_url=str(user.avatar_url),
            created_at=user.created_at,
            updated_at=user.updated_at,
            scanned_at=user.scanned_at,
            last_login_at=user.last_login_at,
            google_refresh_token=user.google_refresh_token,
            subscription_uuids=user.subscription_uuids,
            is_admin=user.is_admin
        )

    def to_domain_user(self) -> User:
        return User(
            uuid=self.uuid,
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
            locale=self.locale,
            avatar_url=utils.parse_url(self.avatar_url),
            created_at=self.created_at,
            updated_at=self.updated_at,
            scanned_at=self.scanned_at,
            last_login_at=self.last_login_at,
            google_refresh_token=self.google_refresh_token,
            subscription_uuids=self.subscription_uuids,
            is_admin=self.is_admin
        )


class MongoDBUserRepository(UserRepository):
    _collection_name: str = 'users'

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

    async def add(self, user: User) -> None:
        try:
            await self._collection().insert_one(MongoDBUser.from_domain_user(user).model_dump())
        except DuplicateKeyError as error:
            if error.details is not None and 'email_unique' in error.details.get('errmsg', ''):
                raise EmailAlreadyInUse(f"Email '{user.email}' is already in use") from error

    async def get(self, user_id: UUID) -> Optional[User]:
        user = await self._collection().find_one({'uuid': user_id, 'deleted_at': None})
        if user is None:
            return None
        user.pop('_id', None)
        return MongoDBUser(**user).to_domain_user()

    async def get_by_email(self, email: str) -> Optional[User]:
        user = await self._collection().find_one({'email': email, 'deleted_at': None})
        if user is None:
            return None
        user.pop('_id', None)
        return MongoDBUser(**user).to_domain_user()

    async def delete(self, user_id: UUID) -> None:
        await self._collection().update_one(
            {'uuid': user_id},
            {'$set': {'deleted_at': datetime.now(timezone.utc)}})

    async def update(self, user: User) -> None:
        await self._collection().update_one(
            {'uuid': user.uuid},
            {'$set': MongoDBUser.from_domain_user(user).model_dump()})

    async def find_latest_scan_before(self, timestamp: datetime) -> List[User]:
        users = await self._collection().find(
            {'scanned_at': {'$lt': timestamp}, 'deleted_at': None}
        ).to_list(length=None)
        return [MongoDBUser(**user).to_domain_user() for user in users]

    async def find_users_subscribed_to_subscription(self, subscription_id: UUID) -> List[User]:
        users = await self._collection().find(
            {'subscription_uuids': subscription_id, 'deleted_at': None}
        ).to_list(length=None)
        return [MongoDBUser(**user).to_domain_user() for user in users]
