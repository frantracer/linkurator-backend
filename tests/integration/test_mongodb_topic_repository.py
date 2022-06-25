import datetime
from ipaddress import IPv4Address
from unittest import mock
from unittest.mock import MagicMock
import uuid

from math import floor
import pytest

from linkurator_core.application.exceptions import DuplicatedKeyError
from linkurator_core.domain.topic import Topic
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.topic_repository import MongoDBTopic, MongoDBTopicRepository


@pytest.fixture(name="topic_repo", scope="session")
def fixture_topic_repo(db_name) -> MongoDBTopicRepository:
    return MongoDBTopicRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


def test_exception_is_raised_if_topics_collection_is_not_created():
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        MongoDBTopicRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")


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


def test_get_topics_by_user_id(topic_repo: MongoDBTopicRepository):
    user_uuid = uuid.UUID("fb0b5160-7704-4310-9bea-d7045574290b")
    topic1 = Topic(name="test_topic_1", uuid=uuid.UUID("33d0aa86-9c70-40d1-8eb2-b402249d2511"),
                   user_id=user_uuid, subscriptions_ids=[],
                   created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    topic2 = Topic(name="test_topic_2", uuid=uuid.UUID("24d56f9d-a1ca-4736-aa45-9beb18cd109d"),
                   user_id=user_uuid, subscriptions_ids=[],
                   created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    topic_repo.add(topic1)
    topic_repo.add(topic2)
    the_topics = topic_repo.get_by_user_id(user_uuid)

    assert len(the_topics) == 2
    assert the_topics[0].uuid in [topic1.uuid, topic2.uuid]
    assert the_topics[1].uuid in [topic1.uuid, topic2.uuid]


def test_update_topic_parameters(topic_repo: MongoDBTopicRepository):
    topic = Topic(name="test",
                  uuid=uuid.UUID("634b81ca-9dde-4bb9-b573-0c6b2cb958df"),
                  user_id=uuid.UUID("0362d52f-6e05-48f9-8144-e3483bbd2517"),
                  subscriptions_ids=[uuid.UUID("680dde6c-7982-48b6-9dfb-51235852d2e5")],
                  created_at=datetime.datetime.fromtimestamp(0),
                  updated_at=datetime.datetime.fromtimestamp(0))

    topic_repo.add(topic)

    topic.name = "new_name"
    topic.subscriptions_ids = [uuid.UUID("f7740d31-c74b-43c9-a8f8-4f5c79bd16d4"),
                               uuid.UUID("f004114c-0790-440c-8bec-fe1c43f55140")]
    topic.updated_at = datetime.datetime.fromtimestamp(1)

    topic_repo.update(topic)
    the_topic = topic_repo.get(topic.uuid)

    assert the_topic is not None
    assert the_topic.name == topic.name
    assert the_topic.uuid == topic.uuid
    assert the_topic.user_id == topic.user_id
    assert the_topic.subscriptions_ids == topic.subscriptions_ids
    assert int(the_topic.created_at.timestamp() * 100) == floor(topic.created_at.timestamp() * 100)
    assert int(the_topic.updated_at.timestamp() * 100) == floor(topic.updated_at.timestamp() * 100)


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


def test_create_topic_with_same_raises_duplicated_key_exception(topic_repo: MongoDBTopicRepository):
    topic = Topic.new(
        name="test",
        uuid=uuid.UUID("a0825ffa-9671-4114-b801-c1df2e71df13"),
        user_id=uuid.UUID("6338822a-41b9-4770-93ce-b7b1a535f904"))

    topic_repo.add(topic)
    with pytest.raises(DuplicatedKeyError):
        topic_repo.add(topic)
