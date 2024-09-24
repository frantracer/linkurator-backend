from uuid import UUID

import pytest

from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.common.mock_factory import mock_user, mock_topic
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_topic_handler() -> None:
    user_repo_mock = InMemoryUserRepository()
    user = mock_user()
    await user_repo_mock.add(user)

    topic = mock_topic(user_uuid=user.uuid)

    topic_repo_mock = InMemoryTopicRepository()
    await topic_repo_mock.add(topic)

    handler = GetTopicHandler(topic_repo_mock, user_repo_mock)

    response = await handler.handle(topic.uuid)

    assert response.topic == topic
    assert response.curator == user


@pytest.mark.asyncio
async def test_get_topic_handler_not_found() -> None:
    user_repo_mock = InMemoryUserRepository()
    topic_repo_mock = InMemoryTopicRepository()

    handler = GetTopicHandler(topic_repo_mock, user_repo_mock)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(UUID('642279d0-9a75-4422-af17-b03446282160'))
