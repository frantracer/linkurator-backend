import uuid
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest

from linkurator_core.application.users.update_user_subscriptions_handler import UpdateYoutubeUserSubscriptionsHandler
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import InvalidCredentialError
from linkurator_core.domain.common.mock_factory import mock_sub, mock_user
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_update_user_subscriptions_with_a_subscription_that_is_not_registered() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    sub1 = mock_sub()
    subscription_service.get_subscriptions.return_value = [sub1]
    subscription_repository = InMemorySubscriptionRepository()

    user_repository = InMemoryUserRepository()
    user = mock_user()
    await user_repository.add(user)

    event_bus_service = AsyncMock(spec=EventBusService)
    handler = UpdateYoutubeUserSubscriptionsHandler(youtube_subscription_service=subscription_service,
                                                    user_repository=user_repository,
                                                    subscription_repository=subscription_repository,
                                                    event_bus_service=event_bus_service)
    await handler.handle(user_id=user.uuid, access_token="access_token")

    assert await subscription_repository.get(sub1.uuid) == sub1

    user_input = await user_repository.get(user.uuid)
    assert user_input is not None
    assert user_input.uuid == user.uuid
    assert user_input.get_subscriptions() == {sub1.uuid}
    assert user_input.scanned_at > user.scanned_at


@pytest.mark.asyncio()
async def test_update_user_subscription_with_subscription_that_is_already_registered() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    url = "https://www.youtube.com/channel/UC1234567890"
    sub1 = mock_sub(url=url)
    sub2 = mock_sub(url=url)
    subscription_service.get_subscriptions.return_value = [sub1]
    subscription_repository = InMemorySubscriptionRepository()
    await subscription_repository.add(sub2)

    user_repository = InMemoryUserRepository()
    user = mock_user()
    await user_repository.add(user)

    event_bus_service = AsyncMock(spec=EventBusService)
    handler = UpdateYoutubeUserSubscriptionsHandler(youtube_subscription_service=subscription_service,
                                                    user_repository=user_repository,
                                                    subscription_repository=subscription_repository,
                                                    event_bus_service=event_bus_service)
    await handler.handle(user_id=user.uuid, access_token="access_token")

    assert await subscription_repository.get(sub1.uuid) is None

    user_input = await user_repository.get(user.uuid)
    assert user_input is not None
    assert user_input.get_subscriptions() == {sub2.uuid}


@pytest.mark.asyncio()
async def test_update_subscriptions_for_non_existing_user_does_nothing() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_repository = MagicMock(spec=SubscriptionRepository)
    user_repository = MagicMock(spec=UserRepository)
    user_repository.get.return_value = None

    event_bus_service = AsyncMock(spec=EventBusService)
    handler = UpdateYoutubeUserSubscriptionsHandler(youtube_subscription_service=subscription_service,
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
async def test_update_subscriptions_for_user_with_invalid_refresh_token_only_updates_scanned_at() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_service.get_subscriptions.side_effect = InvalidCredentialError("Invalid refresh token")
    subscription_repository = MagicMock(spec=SubscriptionRepository)
    user_repository = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repository.get.return_value = deepcopy(user)

    event_bus_service = AsyncMock(spec=EventBusService)
    handler = UpdateYoutubeUserSubscriptionsHandler(youtube_subscription_service=subscription_service,
                                                    user_repository=user_repository,
                                                    subscription_repository=subscription_repository,
                                                    event_bus_service=event_bus_service)
    await handler.handle(user_id=user.uuid, access_token="access_token")

    assert subscription_service.get_subscriptions.call_count == 1
    assert user_repository.update.call_count == 1
    user_input: User = user_repository.update.call_args[0][0]
    assert user_input.uuid == user.uuid
    assert user_input.get_youtube_subscriptions() == user.get_subscriptions()
    assert user_input.scanned_at > user.scanned_at
