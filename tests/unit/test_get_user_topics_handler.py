from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.common.mock_factory import mock_user, mock_topic
from linkurator_core.domain.topics.followed_topic import FollowedTopic
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio
async def test_get_user_topics_handler() -> None:
    user_repo_mock = AsyncMock(spec=UserRepository)
    user = mock_user(uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'))
    user_repo_mock.get.return_value = user
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic1 = mock_topic(
        uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'),
        user_uuid=user.uuid
    )
    topic_repo_mock.get_by_user_id.return_value = [topic1]
    topic_repo_mock.find_topics.return_value = []
    followed_topics_repo_mock = AsyncMock(spec=FollowedTopicsRepository)
    followed_topics_repo_mock.get_followed_topics.return_value = []

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock, followed_topics_repo_mock)

    response = await handler.handle(user.uuid)

    assert len(response.topics) == 1
    assert response.topics[0] == topic1


@pytest.mark.asyncio
async def test_get_user_topics_handler_user_not_found() -> None:
    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = None

    topic_repo_mock = AsyncMock(spec=TopicRepository)
    followed_topics_repo_mock = AsyncMock(spec=FollowedTopicsRepository)

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock, followed_topics_repo_mock)

    with pytest.raises(UserNotFoundError):
        await handler.handle(UUID('7b444729-aaea-4f0c-8fa3-ef307e164a80'))


@pytest.mark.asyncio
async def test_get_user_topics_with_followed_topics() -> None:
    user_repo_mock = AsyncMock(spec=UserRepository)
    user1 = mock_user(uuid=UUID('f437675d-e21e-4b79-af95-1d33ccfd7cc6'))
    user2 = mock_user(uuid=UUID('ead32543-3ab0-41a3-81de-a7cf751bcbcf'))
    user_repo_mock.get.return_value = user1

    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic1 = mock_topic(
        uuid=UUID('6c2483d0-a811-479c-8234-441686690c47'),
        user_uuid=user1.uuid
    )
    topic2 = mock_topic(
        uuid=UUID('46f1ba37-0360-485e-8393-4f91a8f3ff35'),
        user_uuid=user2.uuid
    )

    topic_repo_mock.get_by_user_id.return_value = [topic1]
    topic_repo_mock.find_topics.return_value = [topic2]

    followed_topics_repo_mock = AsyncMock(spec=FollowedTopicsRepository)
    followed_topic = FollowedTopic.new(user1.uuid, topic2.uuid)
    followed_topics_repo_mock.get_followed_topics.return_value = [followed_topic]

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock, followed_topics_repo_mock)

    response = await handler.handle(user1.uuid)

    assert len(response.topics) == 2
    assert {topic.uuid for topic in response.topics} == {topic1.uuid, topic2.uuid}
    assert response.followed_topics_ids == {topic2.uuid}
