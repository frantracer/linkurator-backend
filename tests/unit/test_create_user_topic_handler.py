from unittest.mock import MagicMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.domain.topics.topic import Topic


@pytest.mark.asyncio
async def test_create_topic_handler() -> None:
    topic_repo_mock = MagicMock()
    topic_repo_mock.add.return_value = None
    handler = CreateTopicHandler(topic_repository=topic_repo_mock)

    topic = Topic.new(
        user_id=UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b'),
        name='Topic 1',
        uuid=UUID('615035e7-7d11-41e1-ac29-66ae824e7530')
    )

    await handler.handle(topic)

    assert topic_repo_mock.add.called
    assert topic_repo_mock.add.call_args[0][0] == topic
