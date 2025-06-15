from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


@pytest.mark.asyncio()
async def test_delete_user_topic_handler() -> None:
    user_id = UUID("b5a1e8af-f6e8-493d-a21a-d736d248d1d3")
    topic = Topic.new(
        uuid=UUID("54171165-d162-4372-9ff2-ec778063d531"),
        user_id=user_id,
        name="Test Topic",
    )

    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = topic

    handler = DeleteUserTopicHandler(topic_repo_mock)

    await handler.handle(user_id, topic.uuid)

    assert topic_repo_mock.get.call_count == 1
    assert topic_repo_mock.delete.call_count == 1
    assert topic_repo_mock.delete.call_args == ((topic.uuid,),)


@pytest.mark.asyncio()
async def test_delete_non_existent_topic_raises_exception() -> None:
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = None

    handler = DeleteUserTopicHandler(topic_repo_mock)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(user_id=UUID("4bd5a27e-6436-432f-91a7-e76e1ddc3f82"),
                             topic_id=UUID("755f0161-2d16-4989-949d-e4c0cd2b40af"))


@pytest.mark.asyncio()
async def test_delete_topic_with_different_user_raises_exception() -> None:
    user_id = UUID("1d4f1e32-e2ec-4895-a99e-a102fecb19d8")
    topic = Topic.new(
        uuid=UUID("c104e3d2-ce40-4d34-b434-f044f0bd3c86"),
        user_id=UUID("ce354b5a-ccc4-4cde-bff8-2e89464ba81a"),
        name="Test Topic",
    )

    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = topic

    handler = DeleteUserTopicHandler(topic_repo_mock)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(user_id, topic.uuid)
