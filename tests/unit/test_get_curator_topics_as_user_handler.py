import pytest

from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsHandler
from linkurator_core.domain.common.mock_factory import mock_user, mock_topic
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_curator_topics_handler() -> None:
    user_repo_mock = InMemoryUserRepository()
    curator = mock_user()
    await user_repo_mock.add(curator)

    mocked_topic_1 = mock_topic(user_uuid=curator.uuid)
    mocked_topic_2 = mock_topic(user_uuid=curator.uuid)
    topic_repo_mock = InMemoryTopicRepository()
    await topic_repo_mock.add(mocked_topic_1)
    await topic_repo_mock.add(mocked_topic_2)

    handler = GetCuratorTopicsHandler(
        user_repository=user_repo_mock,
        topic_repository=topic_repo_mock,
    )

    response = await handler.handle(curator_id=curator.uuid)

    assert len(response.topics) == 2
    assert response.topics[0] == mocked_topic_1
    assert response.topics[1] == mocked_topic_2
    assert response.curator == curator
