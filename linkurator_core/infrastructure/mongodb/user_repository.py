from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Optional
from uuid import UUID

import pymongo  # type: ignore
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError  # type: ignore

from linkurator_core.domain.user import User
from linkurator_core.domain.user_repository import UserRepository, EmailAlreadyInUse
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class MongoDBUser(BaseModel):
    uuid: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
    google_refresh_token: str

    @staticmethod
    def from_domain_user(user: User) -> MongoDBUser:
        return MongoDBUser(
            uuid=user.uuid,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
            google_refresh_token=user.google_refresh_token
        )

    def to_domain_user(self) -> User:
        return User(
            uuid=self.uuid,
            name=self.name,
            email=self.email,
            created_at=self.created_at,
            updated_at=self.updated_at,
            google_refresh_token=self.google_refresh_token,
        )


class MongoDBUserRepository(UserRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'users'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password,
                                  uuidRepresentation='standard')
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

    def _user_collection(self) -> pymongo.collection.Collection:
        return self.client.get_database(self.db_name).get_collection(self._collection_name)
