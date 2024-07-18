from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio
async def test_get_user_topics_handler() -> None:
    user_repo_mock = AsyncMock(spec=UserRepository)
    user = User.new(
        uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'),
        first_name='John',
        last_name='Doe',
        email='test@email.com',
        locale='en',
        avatar_url=utils.parse_url('https://example.com/avatar.png'),
        google_refresh_token='refresh_token'
    )
    user_repo_mock.get.return_value = user
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic1 = Topic.new(
        uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'),
        name='Topic 1',
        user_id=user.uuid
    )
    topic_repo_mock.get_by_user_id.return_value = [topic1]

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock)

    topics = await handler.handle(user.uuid)

    assert len(topics) == 1
    assert topics[0] == topic1


@pytest.mark.asyncio
async def test_get_user_topics_handler_user_not_found() -> None:
    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = None

    topic_repo_mock = AsyncMock(spec=TopicRepository)

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock)

    with pytest.raises(UserNotFoundError):
        await handler.handle(UUID('7b444729-aaea-4f0c-8fa3-ef307e164a80'))
