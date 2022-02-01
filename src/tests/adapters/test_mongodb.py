import datetime
import ipaddress
import uuid
from math import floor
from unittest import mock
from unittest.mock import MagicMock

import pytest
from application.adapters.mongodb import MongoDBUserRepository, MongoDBTopicRepository, MongoDBSubscriptionRepository, \
    MongoDBItemRepository, MongoDBUser, MongoDBTopic, MongoDBSubscription, MongoDBItem
from application.domain.model import User, Topic, Subscription, Item
from common import utils


@pytest.fixture(name="db_name", scope="session")
def fixture_db_name() -> str:
    db_name = f'test-{datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}'
    return db_name


@pytest.fixture(name="user_repo", scope="session")
def fixture_user_repo(db_name) -> MongoDBUserRepository:
    return MongoDBUserRepository(ipaddress.IPv4Address('127.0.0.1'), 27017, db_name)


@pytest.fixture(name="topic_repo", scope="session")
def fixture_topic_repo(db_name) -> MongoDBTopicRepository:
    return MongoDBTopicRepository(ipaddress.IPv4Address('127.0.0.1'), 27017, db_name)


@pytest.fixture(name="subscription_repo", scope="session")
def fixture_subscription_repo(db_name) -> MongoDBSubscriptionRepository:
    return MongoDBSubscriptionRepository(ipaddress.IPv4Address('127.0.0.1'), 27017, db_name)


@pytest.fixture(name="item_repo", scope="session")
def fixture_item_repo(db_name) -> MongoDBItemRepository:
    return MongoDBItemRepository(ipaddress.IPv4Address('127.0.0.1'), 27017, db_name)


def test_add_user_to_mongodb(user_repo: MongoDBUserRepository):
    user = User(name="test", email="test@test.com", uuid=uuid.UUID("679c6db9-a54e-4947-b825-57a96fb5f599"),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())

    user_repo.add(user)
    the_user = user_repo.get(user.uuid)

    assert the_user is not None
    assert the_user.name == user.name
    assert the_user.email == user.email
    assert the_user.uuid == user.uuid
    assert int(the_user.created_at.timestamp() * 100) == floor(user.created_at.timestamp() * 100)
    assert int(the_user.updated_at.timestamp() * 100) == floor(user.updated_at.timestamp() * 100)


def test_get_user_that_does_not_exist(user_repo: MongoDBUserRepository):
    the_user = user_repo.get(uuid.UUID("c04c2880-6376-4fe1-a0bf-eac1ae0801ad"))

    assert the_user is None


def test_get_user_with_invalid_format_raises_an_exception(user_repo: MongoDBUserRepository):
    user_dict = dict(MongoDBUser(uuid=uuid.UUID("449e3bee-6f9b-4cbc-8a09-64a6fcface96"),
                                 name="test", email="test@email.com",
                                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now()))
    user_dict['uuid'] = 'invalid_uuid'
    user_collection_mock = MagicMock()
    user_collection_mock.find_one = MagicMock(return_value=user_dict)
    with mock.patch.object(MongoDBUserRepository, '_user_collection', return_value=user_collection_mock):
        with pytest.raises(ValueError):
            user_repo.get(uuid.UUID("c0d59790-bb68-415b-9be5-79c3088aada0"))


def test_delete_user(user_repo: MongoDBUserRepository):
    user = User(name="test", email="test@test.com", uuid=uuid.UUID("1006a7a9-4c12-4475-9c4a-7c0f6c9f8eb3"),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())

    user_repo.add(user)
    the_user = user_repo.get(user.uuid)
    assert the_user is not None

    user_repo.delete(user.uuid)
    deleted_user = user_repo.get(user.uuid)
    assert deleted_user is None


def test_add_topic(topic_repo: MongoDBTopicRepository):
    topic = Topic(name="test", uuid=uuid.UUID("0cc1102a-11e9-4e14-baa7-4a12e958a987"),
                  user_id=uuid.UUID("f29e5cec-f7c9-410e-a508-1c618612fecb"),
                  subscriptions_ids=[uuid.UUID("28d51a54-08dc-467a-897e-c32263966169")],
                  created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())

    topic_repo.add(topic)
    the_topic = topic_repo.get(topic.uuid)

    assert the_topic is not None
    assert the_topic.name == topic.name
    assert the_topic.uuid == topic.uuid
    assert the_topic.user_id == topic.user_id
    assert the_topic.subscriptions_ids == topic.subscriptions_ids
    assert int(the_topic.created_at.timestamp() * 100) == floor(topic.created_at.timestamp() * 100)
    assert int(the_topic.updated_at.timestamp() * 100) == floor(topic.updated_at.timestamp() * 100)


def test_get_topic_that_does_not_exist(topic_repo: MongoDBTopicRepository):
    the_topic = topic_repo.get(uuid.UUID("b613c205-f99d-43b9-9d63-4b7ebe4119a3"))

    assert the_topic is None


def test_get_topic_with_invalid_format_raises_an_exception(topic_repo: MongoDBTopicRepository):
    topic_dict = dict(MongoDBTopic(uuid=uuid.UUID("3ab7068b-1412-46ed-bc1f-46d5f03542e7"),
                                   user_id=uuid.UUID("a23ba1fc-bccb-4e70-a535-7eeca00dbac0"),
                                   subscriptions_ids=[],
                                   name="test", email="test@email.com",
                                   created_at=datetime.datetime.now(), updated_at=datetime.datetime.now()))
    topic_dict['uuid'] = 'invalid_uuid'
    topic_collection_mock = MagicMock()
    topic_collection_mock.find_one = MagicMock(return_value=topic_dict)
    with mock.patch.object(MongoDBTopicRepository, '_topic_collection', return_value=topic_collection_mock):
        with pytest.raises(ValueError):
            topic_repo.get(uuid.UUID("c0d59790-bb68-415b-9be5-79c3088aada0"))


def test_delete_topic(topic_repo: MongoDBTopicRepository):
    topic = Topic(name="test", uuid=uuid.UUID("abc2130f-5a83-499f-a3dc-3115b483f6ba"),
                  user_id=uuid.UUID("1ba6cf89-adc3-4841-9f05-7f3d5dcbf79d"),
                  subscriptions_ids=[uuid.UUID("2eb11f86-b132-402c-a92c-56fff09b3fc5")],
                  created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())

    topic_repo.add(topic)
    the_topic = topic_repo.get(topic.uuid)
    assert the_topic is not None

    topic_repo.delete(topic.uuid)
    deleted_topic = topic_repo.get(topic.uuid)
    assert deleted_topic is None


def test_add_subscription(subscription_repo: MongoDBSubscriptionRepository):
    subscription = Subscription(name="test", uuid=uuid.UUID("8d9e9e1f-c9b4-4b8f-b8c4-c8f1e7b7d9a1"),
                                url=utils.parse_url('https://test.com'),
                                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now(),
                                scanned_at=datetime.datetime(1970, 1, 1, 0, 0, 0, 0))

    subscription_repo.add(subscription)
    the_subscription = subscription_repo.get(subscription.uuid)

    assert the_subscription is not None
    assert the_subscription.name == subscription.name
    assert the_subscription.uuid == subscription.uuid
    assert the_subscription.url == subscription.url
    assert the_subscription.thumbnail == subscription.thumbnail
    assert int(the_subscription.created_at.timestamp() * 100) == floor(subscription.created_at.timestamp() * 100)
    assert int(the_subscription.updated_at.timestamp() * 100) == floor(subscription.updated_at.timestamp() * 100)
    assert int(the_subscription.scanned_at.timestamp() * 100) == floor(subscription.scanned_at.timestamp() * 100)


def test_get_subscription_that_does_not_exist(subscription_repo: MongoDBSubscriptionRepository):
    the_subscription = subscription_repo.get(uuid.UUID("0af092ed-e3f9-4919-8202-c19bfd0627a9"))

    assert the_subscription is None


def test_get_subscription_with_invalid_format_raises_an_exception(subscription_repo: MongoDBSubscriptionRepository):
    subscription_dict = dict(MongoDBSubscription(uuid=uuid.UUID("3ab7068b-1412-46ed-bc1f-46d5f03542e7"),
                                                 name="test", url=utils.parse_url('https://test.com'),
                                                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now(),
                                                 scanned_at=datetime.datetime(1970, 1, 1, 0, 0, 0, 0)))
    subscription_dict['uuid'] = 'invalid_uuid'
    subscription_collection_mock = MagicMock()
    subscription_collection_mock.find_one = MagicMock(return_value=subscription_dict)
    with mock.patch.object(MongoDBSubscriptionRepository, '_subscription_collection',
                           return_value=subscription_collection_mock):
        with pytest.raises(ValueError):
            subscription_repo.get(uuid.UUID("81f7d26c-4a7f-4a27-a081-bb77e034fb30"))


def test_delete_subscription(subscription_repo: MongoDBSubscriptionRepository):
    subscription = Subscription(name="test", uuid=uuid.UUID("0af092ed-e3f9-4919-8202-c19bfd0627a9"),
                                url=utils.parse_url('https://test.com'),
                                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now(),
                                scanned_at=datetime.datetime(1970, 1, 1, 0, 0, 0, 0))

    subscription_repo.add(subscription)
    the_subscription = subscription_repo.get(subscription.uuid)
    assert the_subscription is not None

    subscription_repo.delete(subscription.uuid)
    deleted_subscription = subscription_repo.get(subscription.uuid)
    assert deleted_subscription is None


def test_get_item(item_repo: MongoDBItemRepository):
    item = Item(name="test", uuid=uuid.UUID("9cedfb45-70fb-4283-bfee-993941b05b53"),
                subscription_uuid=uuid.UUID("6ae3792e-6427-4b61-bdc1-66cc9c61fe29"),
                url=utils.parse_url('https://test.com'),
                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    item_repo.add(item)
    the_item = item_repo.get(item.uuid)

    assert the_item is not None
    assert the_item.name == item.name
    assert the_item.uuid == item.uuid
    assert the_item.url == item.url
    assert the_item.thumbnail == item.thumbnail
    assert int(the_item.created_at.timestamp() * 100) == floor(item.created_at.timestamp() * 100)
    assert int(the_item.updated_at.timestamp() * 100) == floor(item.updated_at.timestamp() * 100)


def test_get_item_that_does_not_exist(item_repo: MongoDBItemRepository):
    the_item = item_repo.get(uuid.UUID("88aa425f-28d9-4a25-a87a-8c877cac772d"))

    assert the_item is None


def test_get_item_with_invalid_format_raises_an_exception(item_repo: MongoDBItemRepository):
    item_dict = dict(MongoDBItem(uuid=uuid.UUID("67a06616-e127-4bf0-bcc0-faa221d554c5"),
                                 subscription_uuid=uuid.UUID("9753d304-3a43-414e-a5cd-496672b27c34"),
                                 name="test", url=utils.parse_url('https://test.com'),
                                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now()))
    item_dict['uuid'] = 'invalid_uuid'
    item_collection_mock = MagicMock()
    item_collection_mock.find_one = MagicMock(return_value=item_dict)
    with mock.patch.object(MongoDBItemRepository, '_item_collection',
                           return_value=item_collection_mock):
        with pytest.raises(ValueError):
            item_repo.get(uuid.UUID("756b6b0d-5f54-4099-ae7e-c900666f0a0d"))


def test_delete_item(item_repo: MongoDBItemRepository):
    item = Item(name="test", uuid=uuid.UUID("4bf64498-239e-4bcb-a5a1-b84a7708ad01"),
                subscription_uuid=uuid.UUID("d1dc868b-598c-4547-92d6-011e9b7e38e6"),
                url=utils.parse_url('https://test.com'),
                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    item_repo.add(item)
    the_item = item_repo.get(item.uuid)
    assert the_item is not None

    item_repo.delete(item.uuid)
    deleted_item = item_repo.get(item.uuid)
    assert deleted_item is None
