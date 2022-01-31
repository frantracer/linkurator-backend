from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID
from ipaddress import IPv4Address
from pydantic import AnyUrl
from pymongo import MongoClient  # type: ignore
import pymongo
from application.domain.model import User, Topic, Subscription
from application.service_layer.repositories import AbstractUserRepository, AbstractTopicRepository, \
    AbstractSubscriptionRepository


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

    @staticmethod
    def from_domain_user(user: User) -> 'MongoDBUser':
        return MongoDBUser(
            _id=user.uuid,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    def to_domain_user(self) -> User:
        return User(
            uuid=self.uuid,
            name=self.name,
            email=self.email,
            created_at=self.created_at,
            updated_at=self.updated_at
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
        collection.insert_one(asdict(MongoDBUser.from_domain_user(user)))

    def get(self, user_id: UUID) -> Optional[User]:
        collection = self.client[self.db_name]['users']
        user = collection.find_one({'_id': user_id})
        if user is None:
            return None
        return MongoDBUser(**user).to_domain_user()

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

    @staticmethod
    def from_domain_topic(topic: Topic) -> 'MongoDBTopic':
        return MongoDBTopic(
            _id=topic.uuid,
            name=topic.name,
            subscriptions_ids=topic.subscriptions_ids,
            user_id=topic.user_id,
            created_at=topic.created_at,
            updated_at=topic.updated_at
        )

    def to_domain_topic(self) -> Topic:
        return Topic(
            uuid=self.uuid,
            name=self.name,
            subscriptions_ids=self.subscriptions_ids,
            user_id=self.user_id,
            created_at=self.created_at,
            updated_at=self.updated_at
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
        collection.insert_one(asdict(MongoDBTopic.from_domain_topic(topic)))

    def get(self, topic_id: UUID) -> Optional[Topic]:
        collection = self._topic_collection()
        topic: Optional[Dict] = collection.find_one({'_id': topic_id})
        if topic is None:
            return None
        return MongoDBTopic(**topic).to_domain_topic()

    def delete(self, topic_id: UUID):
        collection = self._topic_collection()
        collection.delete_one({'_id': topic_id})

    def _topic_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name]['topics']


@dataclass
class MongoDBSubscription:
    _id: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime

    @property
    def uuid(self):
        return self._id

    @staticmethod
    def from_domain_subscription(subscription: Subscription) -> 'MongoDBSubscription':
        return MongoDBSubscription(
            _id=subscription.uuid,
            name=subscription.name,
            url=subscription.url,
            thumbnail=subscription.thumbnail,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            scanned_at=subscription.scanned_at
        )

    def to_domain_subscription(self) -> Subscription:
        return Subscription(
            uuid=self.uuid,
            name=self.name,
            url=self.url,
            thumbnail=self.thumbnail,
            created_at=self.created_at,
            updated_at=self.updated_at,
            scanned_at=self.scanned_at
        )


class MongoDBSubscriptionRepository(AbstractSubscriptionRepository):
    client: MongoClient
    db_name: str

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

    def add(self, subscription: Subscription):
        collection = self._subscription_collection()
        collection.insert_one(asdict(MongoDBSubscription.from_domain_subscription(subscription)))

    def get(self, subscription_id: UUID) -> Optional[Subscription]:
        collection = self._subscription_collection()
        subscription: Optional[Dict] = collection.find_one({'_id': subscription_id})
        if subscription is None:
            return None
        return MongoDBSubscription(**subscription).to_domain_subscription()

    def delete(self, subscription_id: UUID):
        collection = self._subscription_collection()
        collection.delete_one({'_id': subscription_id})

    def _subscription_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name]['subscriptions']
