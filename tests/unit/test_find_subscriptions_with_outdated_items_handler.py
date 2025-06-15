from unittest.mock import MagicMock

import pytest

from linkurator_core.application.subscriptions.find_subscriptions_with_outdated_items_handler import (
    FindSubscriptionsWithOutdatedItemsHandler,
)
from linkurator_core.domain.common.event import SubscriptionItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_credential, mock_sub, mock_user
from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio()
async def test_handler_sends_two_events_if_there_are_two_outdated_subscriptions() -> None:
    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    sub1 = mock_sub()
    sub2 = mock_sub()
    sub_repo_mock.find_latest_scan_before.return_value = [sub1, sub2]

    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user1 = mock_user(subscribed_to=[sub1.uuid, sub2.uuid])
    user_repository_mock.find_users_subscribed_to_subscription.return_value = [user1]
    credentials_repository_mock = MagicMock(spec=ExternalCredentialRepository)
    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        external_credentials_repository=credentials_repository_mock)
    await handler.handle()

    assert event_bus_mock.publish.call_count == 2
    arg1 = event_bus_mock.publish.call_args_list[0][0][0]
    arg2 = event_bus_mock.publish.call_args_list[1][0][0]

    assert isinstance(arg1, SubscriptionItemsBecameOutdatedEvent)
    assert isinstance(arg2, SubscriptionItemsBecameOutdatedEvent)

    assert {sub1.uuid, sub2.uuid}.issubset({arg1.subscription_id, arg2.subscription_id})


@pytest.mark.asyncio()
async def test_calculate_subscription_refresh_period_is_5_minutes_if_there_is_one_user_with_no_credentials() -> None:
    sub = mock_sub()
    user = mock_user(subscribed_to=[sub.uuid])

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription.return_value = [user]
    credentials_repository_mock = MagicMock(spec=ExternalCredentialRepository)
    credentials_repository_mock.find_by_users_and_type.return_value = []

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        external_credentials_repository=credentials_repository_mock)

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 5


@pytest.mark.asyncio()
async def test_calculate_subscription_refresh_period_is_1_minute_if_there_is_one_user_and_one_credential() -> None:
    sub = mock_sub()
    user = mock_user(subscribed_to=[sub.uuid])
    credential = mock_credential(user.uuid)

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription.return_value = [user]
    credentials_repository_mock = MagicMock(spec=ExternalCredentialRepository)
    credentials_repository_mock.find_by_users_and_type.return_value = [credential]

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        external_credentials_repository=credentials_repository_mock)

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 1


@pytest.mark.asyncio()
async def test_calculate_subscription_refresh_period_is_1_minute_if_there_is_one_user_and_two_credentials() -> None:
    sub = mock_sub()
    user = mock_user(subscribed_to=[sub.uuid])
    credential1 = mock_credential(user.uuid)
    credential2 = mock_credential(user.uuid)

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription.return_value = [user]
    credentials_repository_mock = MagicMock(spec=ExternalCredentialRepository)
    credentials_repository_mock.find_by_users_and_type.return_value = [credential1, credential2]

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        external_credentials_repository=credentials_repository_mock)

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 1


@pytest.mark.asyncio()
async def test_calculate_subscription_refresh_period_is_24_hours_if_there_is_no_user_subscribed() -> None:
    sub = mock_sub()

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription.return_value = []
    credentials_repository_mock = MagicMock(spec=ExternalCredentialRepository)

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        external_credentials_repository=credentials_repository_mock)

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 60 * 24


@pytest.mark.asyncio()
async def test_calculate_subscription_period_is_6_hours_for_spotify() -> None:
    sub = mock_sub(provider=SubscriptionProvider.SPOTIFY)
    user = mock_user(subscribed_to=[sub.uuid])

    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    event_bus_mock = MagicMock(spec=EventBusService)
    user_repository_mock = MagicMock(spec=UserRepository)
    user_repository_mock.find_users_subscribed_to_subscription.return_value = [user]
    credentials_repository_mock = MagicMock(spec=ExternalCredentialRepository)

    handler = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock,
        user_repository=user_repository_mock,
        external_credentials_repository=credentials_repository_mock)

    assert await handler.calculate_subscription_refresh_period_in_minutes(sub) == 60 * 6
