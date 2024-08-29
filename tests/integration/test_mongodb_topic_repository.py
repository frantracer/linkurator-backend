import uuid
from datetime import datetime, timezone
from ipaddress import IPv4Address
from math import floor
from typing import Any

import pytest

from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.common.mock_factory import mock_topic
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.topic_repository import MongoDBTopicRepository


@pytest.fixture(name="topic_repo", scope="session", params=["mongodb", "in_memory"])
def fixture_topic_repo(db_name: str, request: Any) -> TopicRepository:
    if request.param == "in_memory":
        return InMemoryTopicRepository()
    return MongoDBTopicRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio
async def test_exception_is_raised_if_topics_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBTopicRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio
async def test_add_topic(topic_repo: TopicRepository) -> None:
    topic = Topic(name="test",
                  uuid=uuid.UUID("0cc1102a-11e9-4e14-baa7-4a12e958a987"),
                  user_id=uuid.UUID("f29e5cec-f7c9-410e-a508-1c618612fecb"),
                  subscriptions_ids=[uuid.UUID("28d51a54-08dc-467a-897e-c32263966169")],
                  created_at=datetime.now(tz=timezone.utc),
                  updated_at=datetime.now(tz=timezone.utc))

    await topic_repo.add(topic)
    the_topic = await topic_repo.get(topic.uuid)

    assert the_topic is not None
    assert the_topic.name == topic.name
    assert the_topic.uuid == topic.uuid
    assert the_topic.user_id == topic.user_id
    assert the_topic.subscriptions_ids == topic.subscriptions_ids
    assert int(the_topic.created_at.timestamp() * 100) == floor(topic.created_at.timestamp() * 100)
    assert int(the_topic.updated_at.timestamp() * 100) == floor(topic.updated_at.timestamp() * 100)


@pytest.mark.asyncio
async def test_get_topic_that_does_not_exist(topic_repo: TopicRepository) -> None:
    the_topic = await topic_repo.get(uuid.UUID("b613c205-f99d-43b9-9d63-4b7ebe4119a3"))

    assert the_topic is None


@pytest.mark.asyncio
async def test_get_topics_by_user_id(topic_repo: TopicRepository) -> None:
    user_uuid = uuid.UUID("fb0b5160-7704-4310-9bea-d7045574290b")
    topic1 = Topic(name="test_topic_1",
                   uuid=uuid.UUID("33d0aa86-9c70-40d1-8eb2-b402249d2511"),
                   user_id=user_uuid,
                   subscriptions_ids=[],
                   created_at=datetime.now(tz=timezone.utc),
                   updated_at=datetime.now(tz=timezone.utc))
    topic2 = Topic(name="test_topic_2",
                   uuid=uuid.UUID("24d56f9d-a1ca-4736-aa45-9beb18cd109d"),
                   user_id=user_uuid,
                   subscriptions_ids=[],
                   created_at=datetime.now(tz=timezone.utc),
                   updated_at=datetime.now(tz=timezone.utc))
    await topic_repo.add(topic1)
    await topic_repo.add(topic2)
    the_topics = await topic_repo.get_by_user_id(user_uuid)

    assert len(the_topics) == 2
    assert the_topics[0].uuid in [topic1.uuid, topic2.uuid]
    assert the_topics[1].uuid in [topic1.uuid, topic2.uuid]


@pytest.mark.asyncio
async def test_update_topic_parameters(topic_repo: TopicRepository) -> None:
    topic = Topic(name="test",
                  uuid=uuid.UUID("634b81ca-9dde-4bb9-b573-0c6b2cb958df"),
                  user_id=uuid.UUID("0362d52f-6e05-48f9-8144-e3483bbd2517"),
                  subscriptions_ids=[uuid.UUID("680dde6c-7982-48b6-9dfb-51235852d2e5")],
                  created_at=datetime.fromtimestamp(0, tz=timezone.utc),
                  updated_at=datetime.fromtimestamp(0, tz=timezone.utc))

    await topic_repo.add(topic)

    topic.name = "new_name"
    topic.subscriptions_ids = [uuid.UUID("f7740d31-c74b-43c9-a8f8-4f5c79bd16d4"),
                               uuid.UUID("f004114c-0790-440c-8bec-fe1c43f55140")]
    topic.updated_at = datetime.fromtimestamp(1, tz=timezone.utc)

    await topic_repo.update(topic)
    the_topic = await topic_repo.get(topic.uuid)

    assert the_topic is not None
    assert the_topic.name == topic.name
    assert the_topic.uuid == topic.uuid
    assert the_topic.user_id == topic.user_id
    assert the_topic.subscriptions_ids == topic.subscriptions_ids
    assert int(the_topic.created_at.timestamp() * 100) == floor(topic.created_at.timestamp() * 100)
    assert int(the_topic.updated_at.timestamp() * 100) == floor(topic.updated_at.timestamp() * 100)


@pytest.mark.asyncio
async def test_delete_topic(topic_repo: TopicRepository) -> None:
    topic = Topic(name="test",
                  uuid=uuid.UUID("abc2130f-5a83-499f-a3dc-3115b483f6ba"),
                  user_id=uuid.UUID("1ba6cf89-adc3-4841-9f05-7f3d5dcbf79d"),
                  subscriptions_ids=[uuid.UUID("2eb11f86-b132-402c-a92c-56fff09b3fc5")],
                  created_at=datetime.now(tz=timezone.utc),
                  updated_at=datetime.now(tz=timezone.utc))

    await topic_repo.add(topic)
    the_topic = await topic_repo.get(topic.uuid)
    assert the_topic is not None

    await topic_repo.delete(topic.uuid)
    deleted_topic = await topic_repo.get(topic.uuid)
    assert deleted_topic is None


@pytest.mark.asyncio
async def test_create_topic_with_same_raises_duplicated_key_exception(topic_repo: TopicRepository) -> None:
    topic = Topic.new(
        name="test",
        uuid=uuid.UUID("a0825ffa-9671-4114-b801-c1df2e71df13"),
        user_id=uuid.UUID("6338822a-41b9-4770-93ce-b7b1a535f904"))

    await topic_repo.add(topic)
    with pytest.raises(DuplicatedKeyError):
        await topic_repo.add(topic)


@pytest.mark.asyncio
async def test_find_one_existing_and_non_existing_topics_returns_only_one_topic(
        topic_repo: TopicRepository
) -> None:
    topic1 = Topic.new(
        name="test_topic_1",
        uuid=uuid.UUID("0bfd4fee-99c2-43bb-8178-cc8b324917d2"),
        user_id=uuid.UUID("59819801-ee52-4f80-bbcb-06c65659ff41"))
    topic2 = Topic.new(
        name="test_topic_2",
        uuid=uuid.UUID("f159a3e3-11fe-4198-aae8-8bc016c13830"),
        user_id=uuid.UUID("e2a11fb7-9f4b-492f-a902-3368d8ab80b0"))

    assert len(await topic_repo.find_topics([topic1.uuid, topic2.uuid])) == 0

    await topic_repo.add(topic1)
    topics = await topic_repo.find_topics([topic1.uuid, topic2.uuid])

    assert len(topics) == 1
    assert topics[0].uuid == topic1.uuid


@pytest.mark.asyncio
async def test_find_topics_by_name(topic_repo: TopicRepository) -> None:
    topic1 = mock_topic(name="Leyendas y videojuegos")
    topic2 = mock_topic(name="Fútbol y más")
    topic3 = mock_topic(name="leyendas del fútbol")

    await topic_repo.delete_all()
    await topic_repo.add(topic1)
    await topic_repo.add(topic2)
    await topic_repo.add(topic3)

    found_topics = await topic_repo.find_topics_by_name("videojuegos")
    assert len(found_topics) == 1
    assert found_topics[0].uuid == topic1.uuid

    found_topics = await topic_repo.find_topics_by_name("Leyendas")
    assert len(found_topics) == 2
    assert {topic1.uuid, topic3.uuid} == {sub.uuid for sub in found_topics}

    found_topics = await topic_repo.find_topics_by_name("futbol")
    assert len(found_topics) == 2
    assert {topic2.uuid, topic3.uuid} == {sub.uuid for sub in found_topics}

    found_topics = await topic_repo.find_topics_by_name("mas fútbol")
    assert len(found_topics) == 1
    assert found_topics[0].uuid == topic2.uuid

    found_topics = await topic_repo.find_topics_by_name("baloncesto")
    assert len(found_topics) == 0
