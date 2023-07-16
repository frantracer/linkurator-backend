from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from typing import Dict, Optional
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from pydantic.main import BaseModel
import pymongo  # type: ignore
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError  # type: ignore

from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


class TokenAlreadyExists(Exception):
    pass


class MongoDBSession(BaseModel):
    token: str
    user_id: UUID
    expires_at: datetime

    @staticmethod
    def from_domain_session(session: Session) -> MongoDBSession:
        return MongoDBSession(
            token=session.token,
            user_id=session.user_id,
            expires_at=session.expires_at
        )

    def to_domain_session(self) -> Session:
        return Session(
            token=self.token,
            user_id=self.user_id,
            expires_at=self.expires_at
        )


class MongoDBSessionRepository(SessionRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'sessions'

    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', username=username, password=password)
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, session: Session):
        collection = self._session_collection()
        try:
            collection.insert_one(dict(MongoDBSession.from_domain_session(session)))
        except DuplicateKeyError as error:
            raise TokenAlreadyExists(f"Token '{session.token}' already exists") from error

    def get(self, token: str) -> Optional[Session]:
        collection = self._session_collection()
        session: Optional[Dict] = collection.find_one({'token': token})
        if session is None:
            return None
        return MongoDBSession(**session).to_domain_session()

    def delete(self, token: str):
        collection = self._session_collection()
        collection.delete_one({'token': token})

    def _session_collection(self) -> pymongo.collection.Collection:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.client.get_database(self.db_name).get_collection(
            self._collection_name,
            codec_options=codec_options)
