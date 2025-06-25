from uuid import UUID

import pytest

from linkurator_core.application.topics.favorite_topic_handler import FavoriteTopicHandler
from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.common.mock_factory import mock_topic, mock_user
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_favorite_topic() -> None:
    user = mock_user()
    topic = mock_topic()

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = FavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid in updated_user.get_favorite_topics()


@pytest.mark.asyncio()
async def test_user_can_favorite_own_topic() -> None:
    user = mock_user()
    topic = mock_topic(user_uuid=user.uuid)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    handler = FavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid in updated_user.get_favorite_topics()


@pytest.mark.asyncio()
async def test_cannot_favorite_non_existent_topic() -> None:
    user = mock_user()
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    topic_repo = InMemoryTopicRepository()

    handler = FavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(user_id=user.uuid, topic_id=UUID("8ff7610d-9f72-4eb5-83b9-e721fbcf61d6"))


@pytest.mark.asyncio()
async def test_favorite_topic_with_non_existent_user_does_nothing() -> None:
    topic = mock_topic()
    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    user_repo = InMemoryUserRepository()

    handler = FavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    # Should not raise an exception
    await handler.handle(user_id=UUID("8ff7610d-9f72-4eb5-83b9-e721fbcf61d6"), topic_id=topic.uuid)


@pytest.mark.asyncio()
async def test_favorite_topic_twice_only_adds_once() -> None:
    user = mock_user()
    topic = mock_topic()

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = FavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)
    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.get_favorite_topics() == {topic.uuid}
