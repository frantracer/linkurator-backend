from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsAsUserHandler
from linkurator_core.domain.common.mock_factory import mock_user, mock_topic
from linkurator_core.domain.topics.followed_topic import FollowedTopic
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_curator_topics_as_user_handler() -> None:
    user_repo_mock = InMemoryUserRepository()
    curator = mock_user()
    user = mock_user()
    await user_repo_mock.add(curator)
    await user_repo_mock.add(user)

    mocked_topic_1 = mock_topic(user_uuid=curator.uuid)
    mocked_topic_2 = mock_topic(user_uuid=curator.uuid)
    topic_repo_mock = InMemoryTopicRepository()
    await topic_repo_mock.add(mocked_topic_1)
    await topic_repo_mock.add(mocked_topic_2)

    followed_topics_repo_mock = AsyncMock(spec=FollowedTopicsRepository)
    followed_topics_repo_mock.get_followed_topics.return_value = [
        FollowedTopic.new(user_uuid=user.uuid, topic_uuid=mocked_topic_1.uuid)
    ]

    handler = GetCuratorTopicsAsUserHandler(
        user_repository=user_repo_mock,
        topic_repository=topic_repo_mock,
        followed_topics_repository=followed_topics_repo_mock
    )

    response = await handler.handle(curator_id=curator.uuid, user_id=user.uuid)

    assert len(response) == 2
    assert response[0].topic == mocked_topic_1
    assert response[0].followed is True
    assert response[1].topic == mocked_topic_2
    assert response[1].followed is False
