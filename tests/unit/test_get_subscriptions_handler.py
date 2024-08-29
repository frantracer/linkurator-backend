import pytest

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.common.mock_factory import mock_user, mock_sub
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_subscriptions() -> None:
    sub_repo = InMemorySubscriptionRepository()

    sub = mock_sub()
    await sub_repo.add(sub)

    user = mock_user(subscribed_to=[sub.uuid])
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = GetUserSubscriptionsHandler(sub_repo, user_repo)

    the_subscriptions = await handler.handle(user_id=user.uuid)

    assert the_subscriptions == [sub]
