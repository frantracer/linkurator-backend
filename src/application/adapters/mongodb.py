from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID
from ipaddress import IPv4Address
from pymongo import MongoClient  # type: ignore
import pymongo
from application.domain.model import User, Topic
from application.service_layer.repositories import AbstractUserRepository, AbstractTopicRepository


@dataclass
class MongoDBUser:
    _id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime

    @property
    def uuid(self):
        return self._id


def domain_user_to_db_user(user: User) -> MongoDBUser:
    return MongoDBUser(
        _id=user.uuid,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


def db_user_to_domain_user(db_user: MongoDBUser) -> User:
    return User(
        uuid=db_user.uuid,
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
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

    def add(self, user: User):
        collection = self.client[self.db_name]['users']
        collection.insert_one(asdict(domain_user_to_db_user(user)))

    def get(self, user_id: UUID) -> Optional[User]:
        collection = self.client[self.db_name]['users']
        user = collection.find_one({'_id': user_id})
        if user is None:
            return None
        return db_user_to_domain_user(MongoDBUser(**user))

    def delete(self, user_id: UUID):
        collection = self.client[self.db_name]['users']
        collection.delete_one({'_id': user_id})


@dataclass
class MongoDBTopic:
    _id: UUID
    name: str
    user_id: UUID
    subscriptions_ids: List[UUID]
    created_at: datetime
    updated_at: datetime

    @property
    def uuid(self):
        return self._id


def domain_topic_to_db_topic(topic: Topic) -> MongoDBTopic:
    return MongoDBTopic(
        _id=topic.uuid,
        name=topic.name,
        subscriptions_ids=topic.subscriptions_ids,
        user_id=topic.user_id,
        created_at=topic.created_at,
        updated_at=topic.updated_at
    )


def db_topic_to_domain_topic(db_topic: MongoDBTopic) -> Topic:
    return Topic(
        uuid=db_topic.uuid,
        name=db_topic.name,
        subscriptions_ids=db_topic.subscriptions_ids,
        user_id=db_topic.user_id,
        created_at=db_topic.created_at,
        updated_at=db_topic.updated_at
    )


class MongoDBTopicRepository(AbstractTopicRepository):
    client: MongoClient
    db_name: str

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

    def add(self, topic: Topic):
        collection = self._topic_collection()
        collection.insert_one(asdict(domain_topic_to_db_topic(topic)))

    def get(self, topic_id: UUID) -> Optional[Topic]:
        collection = self._topic_collection()
        topic: Optional[Dict] = collection.find_one({'_id': topic_id})
        if topic is None:
            return None
        return db_topic_to_domain_topic(MongoDBTopic(**topic))

    def delete(self, topic_id: UUID):
        collection = self._topic_collection()
        collection.delete_one({'_id': topic_id})

    def _topic_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name]['topics']
