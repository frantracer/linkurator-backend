import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from linkurator_core.application.users.update_patreon_user_subscriptions_handler import (
    UpdatePatreonUserSubscriptionsHandler,
)
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_sub, mock_user
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_update_patreon_subscriptions_with_already_registered_subscription() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    url = "https://www.patreon.com/creator"
    sub1 = mock_sub(url=url, provider="patreon")
    sub2 = mock_sub(url=url, provider="patreon")
    subscription_service.get_subscriptions.return_value = [sub1]
    subscription_repository = InMemorySubscriptionRepository()
    await subscription_repository.add(sub2)

    user_repository = InMemoryUserRepository()
    user = mock_user()
    await user_repository.add(user)

    event_bus_service = AsyncMock(spec=EventBusService)
    handler = UpdatePatreonUserSubscriptionsHandler(patreon_subscription_service=subscription_service,
                                                    user_repository=user_repository,
                                                    subscription_repository=subscription_repository,
                                                    event_bus_service=event_bus_service)
    await handler.handle(user_id=user.uuid, access_token="access_token")

    assert await subscription_repository.get(sub1.uuid) is None

    updated_user = await user_repository.get(user.uuid)
    assert updated_user is not None
    assert sub2.uuid in updated_user.get_subscriptions()

    event_bus_service.publish.assert_not_called()


@pytest.mark.asyncio()
async def test_update_patreon_subscriptions_for_non_existing_user_does_nothing() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_repository = MagicMock(spec=SubscriptionRepository)
    user_repository = MagicMock(spec=UserRepository)
    user_repository.get.return_value = None

    event_bus_service = AsyncMock(spec=EventBusService)
    handler = UpdatePatreonUserSubscriptionsHandler(patreon_subscription_service=subscription_service,
                                                    user_repository=user_repository,
                                                    subscription_repository=subscription_repository,
                                                    event_bus_service=event_bus_service)
    user_id = uuid.UUID("3577da9f-2d85-4475-9aaf-5f38cd01bc2a")
    await handler.handle(user_id=user_id, access_token="access_token")

    assert subscription_service.get_subscriptions.call_count == 0
    assert user_repository.update.call_count == 0
    assert user_repository.get.call_count == 1
    assert user_repository.get.call_args[0][0] == user_id


@pytest.mark.asyncio()
async def test_update_patreon_subscriptions_with_multiple_subscriptions() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    sub1 = mock_sub(provider="patreon")
    sub2 = mock_sub(provider="patreon")
    subscription_service.get_subscriptions.return_value = [sub1, sub2]
    subscription_repository = InMemorySubscriptionRepository()

    user_repository = InMemoryUserRepository()
    user = mock_user()
    await user_repository.add(user)

    event_bus_service = AsyncMock(spec=EventBusService)
    handler = UpdatePatreonUserSubscriptionsHandler(patreon_subscription_service=subscription_service,
                                                    user_repository=user_repository,
                                                    subscription_repository=subscription_repository,
                                                    event_bus_service=event_bus_service)
    await handler.handle(user_id=user.uuid, access_token="access_token")

    assert await subscription_repository.get(sub1.uuid) == sub1
    assert await subscription_repository.get(sub2.uuid) == sub2

    updated_user = await user_repository.get(user.uuid)
    assert updated_user is not None
    assert sub1.uuid in updated_user.get_subscriptions()
    assert sub2.uuid in updated_user.get_subscriptions()

    assert event_bus_service.publish.call_count == 2
