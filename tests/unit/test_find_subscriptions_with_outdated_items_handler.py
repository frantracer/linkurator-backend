from unittest.mock import AsyncMock, MagicMock

import pytest

from linkurator_core.application.subscriptions.find_subscriptions_with_outdated_items_handler import (
    FindSubscriptionsWithOutdatedItemsHandler,
)
from linkurator_core.domain.common.event import SubscriptionItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_sub, mock_user
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user_repository import UserRepository


def mock_subscription_service(provider: str, refresh_period: int) -> MagicMock:
    service = MagicMock(spec=SubscriptionService)
    service.provider_name.return_value = provider
    service.refresh_period_minutes.return_value = refresh_period
    return service


@pytest.mark.asyncio()
async def test_handler_sends_two_events_if_there_are_two_outdated_subscriptions() -> None:
    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    sub1 = mock_sub(provider="youtube")
    sub2 = mock_sub(provider="youtube")
    sub_repo_mock.find_latest_scan_before = AsyncMock(return_value=[sub1, sub2])

    event_bus_mock = MagicMock(spec=EventBusService)
    event_bus_mock.publish = AsyncMock()
    user_repository_mock = MagicMock(spec=UserRepository)
    user1 = mock_user(subscribed_to=[sub1.uuid, sub2.uuid])
    user_repository_mock.find_users_subscribed_to_subscription = AsyncMock(return_value=[user1])

    youtube_service = mock_subscription_service("youtube", 1)

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        subscription_services=[youtube_service])
    await handler.handle()

    assert event_bus_mock.publish.call_count == 2
    arg1 = event_bus_mock.publish.call_args_list[0][0][0]
    arg2 = event_bus_mock.publish.call_args_list[1][0][0]

    assert isinstance(arg1, SubscriptionItemsBecameOutdatedEvent)
    assert isinstance(arg2, SubscriptionItemsBecameOutdatedEvent)

    assert {sub1.uuid, sub2.uuid}.issubset({arg1.subscription_id, arg2.subscription_id})


@pytest.mark.asyncio()
async def test_calculate_subscription_refresh_period_is_5_minutes_if_provider_is_not_registered() -> None:
    sub = mock_sub(provider="unknown_provider")
    user = mock_user(subscribed_to=[sub.uuid])

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription = AsyncMock(return_value=[user])

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        subscription_services=[])

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 5


@pytest.mark.asyncio()
async def test_calculate_subscription_refresh_period_uses_provider_refresh_period() -> None:
    sub = mock_sub(provider="youtube")
    user = mock_user(subscribed_to=[sub.uuid])

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription = AsyncMock(return_value=[user])

    youtube_service = mock_subscription_service("youtube", 1)

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        subscription_services=[youtube_service])

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 1


@pytest.mark.asyncio()
async def test_calculate_subscription_refresh_period_is_24_hours_if_there_is_no_user_subscribed() -> None:
    sub = mock_sub()

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription = AsyncMock(return_value=[])

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        subscription_services=[])

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 60 * 24
