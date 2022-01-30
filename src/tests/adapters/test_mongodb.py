import datetime
import ipaddress
import uuid
from math import floor

import pytest

from application.adapters.mongodb import MongoDBUserRepository, MongoDBTopicRepository
from application.domain.model import User, Topic


@pytest.fixture(name="db_name")
def fixture_db_name() -> str:
    db_name = f'test-{datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}'
    return db_name


@pytest.fixture(name="user_repo")
def fixture_user_repo(db_name) -> MongoDBUserRepository:
    return MongoDBUserRepository(ipaddress.IPv4Address('127.0.0.1'), 27017, db_name)


@pytest.fixture(name="topic_repo")
def fixture_topic_repo(db_name) -> MongoDBTopicRepository:
    return MongoDBTopicRepository(ipaddress.IPv4Address('127.0.0.1'), 27017, db_name)


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
