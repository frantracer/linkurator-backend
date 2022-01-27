from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID
from ipaddress import IPv4Address
from pymongo import MongoClient  # type: ignore
from application.domain.model import User
from application.service_layer.repositories import AbstractUserRepository


@dataclass
class MongoDBUser:
    _id: str
    name: str
    email: str
    created_at: datetime
    updated_at: datetime

    @property
    def uuid(self):
        return self._id


def domain_user_to_db_user(user: User) -> MongoDBUser:
    return MongoDBUser(
        _id=str(user.uuid),
        name=user.name,
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


def db_user_to_domain_user(db_user: MongoDBUser) -> User:
    return User(
        uuid=UUID(db_user.uuid),
        name=db_user.name,
        email=db_user.email,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )


class MongoDBUserRepository(AbstractUserRepository):
    client: MongoClient
    db_name: str

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/')
        self.db_name = db_name

    def add(self, user: User):
        collection = self.client[self.db_name]['users']
        collection.insert_one(asdict(domain_user_to_db_user(user)))

    def get(self, user_id: UUID) -> Optional[User]:
        collection = self.client[self.db_name]['users']
        user = collection.find_one({'_id': str(user_id)})
        if user is None:
            return None
        return db_user_to_domain_user(MongoDBUser(**user))

    def delete(self, user_id: UUID):
        collection = self.client[self.db_name]['users']
        collection.delete_one({'_id': str(user_id)})
