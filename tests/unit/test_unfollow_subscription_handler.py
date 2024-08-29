import pytest

from linkurator_core.application.subscriptions.unfollow_subscription_handler import UnfollowSubscriptionHandler
from linkurator_core.domain.common.exceptions import CannotUnfollowAssignedSubscriptionError
from linkurator_core.domain.common.mock_factory import mock_user, mock_sub, mock_topic
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.topic_repository import InMemoryTopicRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_unfollow_subscription() -> None:
    user_repo = InMemoryUserRepository()
    subscription_repo = InMemorySubscriptionRepository()
    topic_repo = InMemoryTopicRepository()

    sub = mock_sub()
    user = mock_user(
        subscribed_to=[sub.uuid]
    )

    await user_repo.add(user)
    await subscription_repo.add(sub)

    handler = UnfollowSubscriptionHandler(
        user_repository=user_repo,
        subscription_repository=subscription_repo,
        topic_repository=topic_repo)

    await handler.handle(user.uuid, sub.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.get_subscriptions() == set()


@pytest.mark.asyncio
async def test_unfollow_subscription_that_does_not_exist() -> None:
    user_repo = InMemoryUserRepository()
    subscription_repo = InMemorySubscriptionRepository()
    topic_repo = InMemoryTopicRepository()

    user = mock_user()

    await user_repo.add(user)

    handler = UnfollowSubscriptionHandler(
        user_repository=user_repo,
        subscription_repository=subscription_repo,
        topic_repository=topic_repo)

    await handler.handle(user.uuid, user.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.get_subscriptions() == set()


@pytest.mark.asyncio
async def test_unfollow_subscription_included_in_a_topic_returns_an_error() -> None:
    user_repo = InMemoryUserRepository()
    subscription_repo = InMemorySubscriptionRepository()
    topic_repo = InMemoryTopicRepository()

    sub = mock_sub()
    user = mock_user(
        subscribed_to=[sub.uuid]
    )
    topic = mock_topic(
        user_uuid=user.uuid,
        subscription_uuids=[sub.uuid]
    )

    await user_repo.add(user)
    await subscription_repo.add(sub)
    await topic_repo.add(topic)

    handler = UnfollowSubscriptionHandler(
        user_repository=user_repo,
        subscription_repository=subscription_repo,
        topic_repository=topic_repo)

    with pytest.raises(CannotUnfollowAssignedSubscriptionError):
        await handler.handle(user.uuid, sub.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.get_subscriptions() == {sub.uuid}
