from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import List, Optional
from uuid import UUID

from bson.codec_options import CodecOptions
from bson.binary import UuidRepresentation
import pymongo  # type: ignore
from pydantic import AnyUrl, BaseModel
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError  # type: ignore

from linkurator_core.common import utils
from linkurator_core.domain.user import User
from linkurator_core.domain.user_repository import UserRepository, EmailAlreadyInUse
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBUser(BaseModel):
    uuid: UUID
    first_name: str
    last_name: str
    email: str
    locale: str = "en"
    avatar_url: AnyUrl = utils.parse_url('https://www.linkurator.com/favicon.ico')
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    last_login_at: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
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
            avatar_url=user.avatar_url,
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
            avatar_url=self.avatar_url,
            created_at=self.created_at,
            updated_at=self.updated_at,
            scanned_at=self.scanned_at,
            last_login_at=self.last_login_at,
            google_refresh_token=self.google_refresh_token,
            subscription_uuids=self.subscription_uuids,
            is_admin=self.is_admin
        )


class MongoDBUserRepository(UserRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'users'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, user: User):
        collection = self._user_collection()
        try:
            collection.insert_one(dict(MongoDBUser.from_domain_user(user)))
        except DuplicateKeyError as error:
            if error.details is not None and 'email_unique' in error.details.get('errmsg', ''):
                raise EmailAlreadyInUse(f"Email '{user.email}' is already in use") from error

    def get(self, user_id: UUID) -> Optional[User]:
        collection = self._user_collection()
        user = collection.find_one({'uuid': user_id})
        if user is None:
            return None
        user.pop('_id', None)
        return MongoDBUser(**user).to_domain_user()

    def get_by_email(self, email: str) -> Optional[User]:
        collection = self._user_collection()
        user = collection.find_one({'email': email})
        if user is None:
            return None
        user.pop('_id', None)
        return MongoDBUser(**user).to_domain_user()

    def delete(self, user_id: UUID):
        collection = self._user_collection()
        collection.delete_one({'uuid': user_id})

    def update(self, user: User):
        collection = self._user_collection()
        collection.update_one({'uuid': user.uuid}, {'$set': dict(MongoDBUser.from_domain_user(user))})

    def find_latest_scan_before(self, timestamp: datetime) -> List[User]:
        collection = self._user_collection()
        users = collection.find({'scanned_at': {'$lt': timestamp}})
        return [MongoDBUser(**user).to_domain_user() for user in users]

    def _user_collection(self) -> pymongo.collection.Collection:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            self._collection_name,
            codec_options=codec_options)
