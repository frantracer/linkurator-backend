from uuid import UUID

import pytest

from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.common.mock_factory import mock_user, mock_topic
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_user_topics_handler() -> None:
    user_repo_mock = InMemoryUserRepository()
    user = mock_user(uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'))
    await user_repo_mock.add(user)
    topic_repo_mock = InMemoryTopicRepository()
    topic1 = mock_topic(
        uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'),
        user_uuid=user.uuid
    )
    await topic_repo_mock.add(topic1)

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock)

    curator_topics = await handler.handle(user.uuid)

    assert len(curator_topics) == 1
    assert curator_topics[0].topic == topic1
    assert curator_topics[0].curator == user


@pytest.mark.asyncio
async def test_get_user_topics_handler_user_not_found() -> None:
    user_repo_mock = InMemoryUserRepository()

    topic_repo_mock = InMemoryTopicRepository()

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock)

    with pytest.raises(UserNotFoundError):
        await handler.handle(UUID('7b444729-aaea-4f0c-8fa3-ef307e164a80'))


@pytest.mark.asyncio
async def test_get_user_topics_with_followed_topics() -> None:
    user1 = mock_user()
    user2 = mock_user()

    topic1 = mock_topic(
        uuid=UUID('6c2483d0-a811-479c-8234-441686690c47'),
        user_uuid=user1.uuid
    )
    topic2 = mock_topic(
        uuid=UUID('46f1ba37-0360-485e-8393-4f91a8f3ff35'),
        user_uuid=user2.uuid
    )

    user1.follow_topic(topic2.uuid)

    user_repo_mock = InMemoryUserRepository()
    await user_repo_mock.add(user1)
    await user_repo_mock.add(user2)

    topic_repo_mock = InMemoryTopicRepository()
    await topic_repo_mock.add(topic1)
    await topic_repo_mock.add(topic2)

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock)

    curator_topics = await handler.handle(user1.uuid)

    assert len(curator_topics) == 2
    assert {element.topic.uuid for element in curator_topics} == {topic1.uuid, topic2.uuid}
    assert {element.curator.uuid for element in curator_topics} == {user1.uuid, user2.uuid}
