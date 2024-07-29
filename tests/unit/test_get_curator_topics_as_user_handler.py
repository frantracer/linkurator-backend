from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsAsUserHandler
from linkurator_core.domain.common.mock_factory import mock_user, mock_topic
from linkurator_core.domain.topics.followed_topic import FollowedTopic
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio
async def test_get_curator_topics_as_user_handler() -> None:
    user_repo_mock = AsyncMock(spec=UserRepository)
    curator = mock_user()
    user = mock_user()

    async def mock_get_user(user_id: UUID) -> User | None:
        if user_id == curator.uuid:
            return curator
        if user_id == user.uuid:
            return user
        return None

    user_repo_mock.get = AsyncMock(side_effect=mock_get_user)

    mocked_topic_1 = mock_topic()
    mocked_topic_2 = mock_topic()
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get_by_user_id.return_value = [
        mocked_topic_1,
        mocked_topic_2
    ]
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
