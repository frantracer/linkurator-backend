import pytest

from linkurator_core.application.subscriptions.follow_subscription_handler import FollowSubscriptionHandler
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError
from linkurator_core.domain.common.mock_factory import mock_sub, mock_user
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_follow_subscription() -> None:
    user_repo = InMemoryUserRepository()
    subscription_repo = InMemorySubscriptionRepository()

    sub = mock_sub()
    user = mock_user()

    await user_repo.add(user)
    await subscription_repo.add(sub)

    handler = FollowSubscriptionHandler(
        subscription_repository=subscription_repo,
        user_repository=user_repo,
    )

    await handler.handle(user.uuid, sub.uuid)

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert sub.uuid in updated_user.get_subscriptions()


@pytest.mark.asyncio()
async def test_follow_subscription_that_does_not_exist() -> None:
    user_repo = InMemoryUserRepository()
    subscription_repo = InMemorySubscriptionRepository()

    user = mock_user()

    await user_repo.add(user)

    handler = FollowSubscriptionHandler(
        subscription_repository=subscription_repo,
        user_repository=user_repo,
    )

    with pytest.raises(SubscriptionNotFoundError):
        await handler.handle(user.uuid, user.uuid)
