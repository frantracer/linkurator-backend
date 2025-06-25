from uuid import UUID

import pytest

from linkurator_core.application.topics.unfavorite_topic_handler import UnfavoriteTopicHandler
from linkurator_core.domain.common.mock_factory import mock_topic, mock_user
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_unfavorite_topic() -> None:
    user = mock_user()
    topic = mock_topic()

    # Start with topic already favorited
    user.favorite_topic(topic.uuid)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid not in updated_user.get_favorite_topics()


@pytest.mark.asyncio()
async def test_unfavorite_topic_not_favorited() -> None:
    user = mock_user()
    topic = mock_topic()

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    # Should not raise an exception even if topic wasn't favorited
    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid not in updated_user.get_favorite_topics()


@pytest.mark.asyncio()
async def test_unfavorite_topic_with_non_existent_user_does_nothing() -> None:
    topic = mock_topic()
    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    user_repo = InMemoryUserRepository()

    handler = UnfavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    # Should not raise an exception
    await handler.handle(user_id=UUID("8ff7610d-9f72-4eb5-83b9-e721fbcf61d6"), topic_id=topic.uuid)


@pytest.mark.asyncio()
async def test_unfavorite_topic_twice_is_safe() -> None:
    user = mock_user()
    topic = mock_topic()

    # Start with topic already favorited
    user.favorite_topic(topic.uuid)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)
    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid not in updated_user.get_favorite_topics()


@pytest.mark.asyncio()
async def test_unfavorite_one_topic_keeps_others() -> None:
    user = mock_user()
    topic1 = mock_topic()
    topic2 = mock_topic()

    # Start with both topics favorited
    user.favorite_topic(topic1.uuid)
    user.favorite_topic(topic2.uuid)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic1)
    await topic_repo.add(topic2)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfavoriteTopicHandler(topic_repository=topic_repo, user_repository=user_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic1.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic1.uuid not in updated_user.get_favorite_topics()
    assert topic2.uuid in updated_user.get_favorite_topics()
