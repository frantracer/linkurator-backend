from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


@pytest.mark.asyncio
async def test_get_topic_handler() -> None:
    topic = Topic.new(
        uuid=UUID('ee7ea21c-9a9a-4c12-ae67-ba9f86a34a9b'),
        user_id=UUID('0e4e5a9d-d2d9-4d04-9707-89301f0d89d4'),
        name='Test Topic',
        subscription_ids=[UUID('263bda19-e32e-47df-a0c5-7884bdafc23f')]
    )

    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = topic

    handler = GetTopicHandler(topic_repo_mock)

    response = await handler.handle(topic.uuid)

    assert response == topic


@pytest.mark.asyncio
async def test_get_topic_handler_not_found() -> None:
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = None

    handler = GetTopicHandler(topic_repo_mock)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(UUID('642279d0-9a75-4422-af17-b03446282160'))
