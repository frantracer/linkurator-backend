from uuid import UUID

import pytest

from linkurator_core.application.topics.unfollow_topic_handler import UnfollowTopicHandler
from linkurator_core.domain.common.mock_factory import mock_topic, mock_user
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_unfollow_topic() -> None:
    user = mock_user()
    topic = mock_topic()

    user.follow_topic(topic.uuid)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfollowTopicHandler(user_repository=user_repo, topic_repository=topic_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid not in updated_user.get_followed_topics()


@pytest.mark.asyncio()
async def test_unfollowing_another_curators_topic_removes_it_from_favorites() -> None:
    user = mock_user()
    topic = mock_topic()

    user.follow_topic(topic.uuid)
    user.favorite_topic(topic.uuid)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfollowTopicHandler(user_repository=user_repo, topic_repository=topic_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid not in updated_user.get_followed_topics()
    assert topic.uuid not in updated_user.get_favorite_topics()


@pytest.mark.asyncio()
async def test_unfollowing_own_topic_keeps_it_in_favorites() -> None:
    user = mock_user()
    topic = mock_topic(user_uuid=user.uuid)

    user.favorite_topic(topic.uuid)

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfollowTopicHandler(user_repository=user_repo, topic_repository=topic_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid in updated_user.get_favorite_topics()


@pytest.mark.asyncio()
async def test_unfollow_topic_not_followed_is_safe() -> None:
    user = mock_user()
    topic = mock_topic()

    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfollowTopicHandler(user_repository=user_repo, topic_repository=topic_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic.uuid not in updated_user.get_followed_topics()


@pytest.mark.asyncio()
async def test_unfollow_topic_with_non_existent_user_does_nothing() -> None:
    topic = mock_topic()
    topic_repo = InMemoryTopicRepository()
    await topic_repo.add(topic)

    user_repo = InMemoryUserRepository()

    handler = UnfollowTopicHandler(user_repository=user_repo, topic_repository=topic_repo)

    await handler.handle(user_id=UUID("8ff7610d-9f72-4eb5-83b9-e721fbcf61d6"), topic_id=topic.uuid)


@pytest.mark.asyncio()
async def test_unfollow_non_existent_topic_still_unfollows() -> None:
    user = mock_user()
    topic_id = UUID("8ff7610d-9f72-4eb5-83b9-e721fbcf61d6")
    user.follow_topic(topic_id)

    topic_repo = InMemoryTopicRepository()
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = UnfollowTopicHandler(user_repository=user_repo, topic_repository=topic_repo)

    await handler.handle(user_id=user.uuid, topic_id=topic_id)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert topic_id not in updated_user.get_followed_topics()
