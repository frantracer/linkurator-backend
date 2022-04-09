import pathlib
from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID
from ipaddress import IPv4Address
from mongodb_migrations.cli import MigrationManager  # type: ignore
from mongodb_migrations.config import Configuration, Execution  # type: ignore
from pydantic import AnyUrl, BaseModel
from pymongo import MongoClient  # type: ignore
import pymongo
from application.domain.user import User
from application.domain.topic import Topic
from application.domain.subscription import Subscription
from application.domain.item import Item
from application.service_layer.repositories import UserRepository, TopicRepository, \
    SubscriptionRepository, ItemRepository


def run_mongodb_migrations(address: IPv4Address, port: int, db_name: str, user: str, password: str) -> None:
    mongodb_migrations_manager = MigrationManager(config=Configuration({
        'mongo_host': str(address),
        'mongo_port': port,
        'mongo_database': db_name,
        'mongo_username': user,
        'mongo_password': password,
        'mongo_migrations_path': f'{pathlib.Path(__file__).parent.absolute()}/mongodb_migrations',
        'metastore': 'database_migrations',
        'execution': Execution.MIGRATE,
        'to_datetime': datetime.now().strftime('%Y%m%d%H%M%S')
    }))

    mongodb_migrations_manager.run()


class CollectionIsNotInitialized(Exception):
    pass


class MongoDBUser(BaseModel):
    uuid: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain_user(user: User) -> 'MongoDBUser':
        return MongoDBUser(
            uuid=user.uuid,
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


class MongoDBUserRepository(UserRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'users'

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, user: User):
        collection = self._user_collection()
        collection.insert_one(dict(MongoDBUser.from_domain_user(user)))

    def get(self, user_id: UUID) -> Optional[User]:
        collection = self._user_collection()
        user = collection.find_one({'uuid': user_id})
        if user is None:
            return None
        user.pop('_id', None)
        return MongoDBUser(**user).to_domain_user()

    def delete(self, user_id: UUID):
        collection = self._user_collection()
        collection.delete_one({'uuid': user_id})

    def _user_collection(self) -> pymongo.collection.Collection:
        return self.client.get_database(self.db_name).get_collection(self._collection_name)


class MongoDBTopic(BaseModel):
    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: List[UUID]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain_topic(topic: Topic) -> 'MongoDBTopic':
        return MongoDBTopic(
            uuid=topic.uuid,
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


class MongoDBTopicRepository(TopicRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'topics'

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, topic: Topic):
        collection = self._topic_collection()
        collection.insert_one(dict(MongoDBTopic.from_domain_topic(topic)))

    def get(self, topic_id: UUID) -> Optional[Topic]:
        collection = self._topic_collection()
        topic: Optional[Dict] = collection.find_one({'uuid': topic_id})
        if topic is None:
            return None
        return MongoDBTopic(**topic).to_domain_topic()

    def delete(self, topic_id: UUID):
        collection = self._topic_collection()
        collection.delete_one({'uuid': topic_id})

    def get_by_user_id(self, user_id: UUID) -> List[Topic]:
        collection = self._topic_collection()
        topics = collection.find({'user_id': user_id})
        return [MongoDBTopic(**topic).to_domain_topic() for topic in topics]

    def _topic_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name][self._collection_name]


class MongoDBSubscription(BaseModel):
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime

    @staticmethod
    def from_domain_subscription(subscription: Subscription) -> 'MongoDBSubscription':
        return MongoDBSubscription(
            uuid=subscription.uuid,
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


class MongoDBSubscriptionRepository(SubscriptionRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'subscriptions'

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, subscription: Subscription):
        collection = self._subscription_collection()
        collection.insert_one(dict(MongoDBSubscription.from_domain_subscription(subscription)))

    def get(self, subscription_id: UUID) -> Optional[Subscription]:
        collection = self._subscription_collection()
        subscription: Optional[Dict] = collection.find_one({'uuid': subscription_id})
        if subscription is None:
            return None
        return MongoDBSubscription(**subscription).to_domain_subscription()

    def delete(self, subscription_id: UUID):
        collection = self._subscription_collection()
        collection.delete_one({'uuid': subscription_id})

    def _subscription_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name][self._collection_name]


class MongoDBItem(BaseModel):
    uuid: UUID
    subscription_uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_domain_item(item: Item) -> 'MongoDBItem':
        return MongoDBItem(
            uuid=item.uuid,
            subscription_uuid=item.subscription_uuid,
            name=item.name,
            url=item.url,
            thumbnail=item.thumbnail,
            created_at=item.created_at,
            updated_at=item.updated_at
        )

    def to_domain_item(self) -> Item:
        return Item(
            uuid=self.uuid,
            subscription_uuid=self.subscription_uuid,
            name=self.name,
            url=self.url,
            thumbnail=self.thumbnail,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class MongoDBItemRepository(ItemRepository):
    client: MongoClient
    db_name: str
    _collection_name: str = 'items'

    def __init__(self, ip: IPv4Address, port: int, db_name: str):
        super().__init__()
        self.client = MongoClient(f'mongodb://{str(ip)}:{port}/', uuidRepresentation='standard')
        self.db_name = db_name

        if self._collection_name not in self.client[self.db_name].list_collection_names():
            raise CollectionIsNotInitialized(
                f"Collection '{self.db_name}' is not initialized in database '{self.db_name}'")

    def add(self, item: Item):
        collection = self._item_collection()
        collection.insert_one(dict(MongoDBItem.from_domain_item(item)))

    def get(self, item_id: UUID) -> Optional[Item]:
        collection = self._item_collection()
        item: Optional[Dict] = collection.find_one({'uuid': item_id})
        if item is None:
            return None
        return MongoDBItem(**item).to_domain_item()

    def delete(self, item_id: UUID):
        collection = self._item_collection()
        collection.delete_one({'uuid': item_id})

    def get_by_subscription_id(self, subscription_id: UUID) -> List[Item]:
        collection = self._item_collection()
        items: List[Dict] = collection.find({'subscription_uuid': subscription_id}) \
            .sort('created_at', pymongo.DESCENDING)
        return [MongoDBItem(**item).to_domain_item() for item in items]

    def _item_collection(self) -> pymongo.collection.Collection:
        return self.client[self.db_name][self._collection_name]
