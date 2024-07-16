from unittest.mock import MagicMock, AsyncMock

import pytest

from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler
from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.common.mock_factory import mock_user, mock_sub, mock_credential
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio
async def test_an_user_can_refresh_a_subscription_if_has_one_uploaded_credential() -> None:
    sub = mock_sub()
    user = mock_user(subscribed_to=[sub.uuid])
    credential = mock_credential(user_id=user.uuid)

    user_repository = AsyncMock(spec=UserRepository)
    user_repository.get.return_value = user

    subscription_repository = MagicMock()
    subscription_repository.get.return_value = sub

    subscription_service = AsyncMock()
    subscription_service.get_subscription.return_value = sub

    credentials_repository = AsyncMock()
    credentials_repository.find_by_users_and_type.return_value = [credential]

    handler = RefreshSubscriptionHandler(
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        credentials_repository=credentials_repository)

    await handler.handle(user_id=user.uuid, subscription_id=sub.uuid)

    assert subscription_service.get_subscription.call_count == 1
    subscription_service.get_subscription.assert_called_once_with(sub_id=sub.uuid, credential=credential)

    assert subscription_repository.update.call_count == 1
    subscription_repository.update.assert_called_once_with(sub)


@pytest.mark.asyncio
async def test_an_user_with_no_credentials_cannot_refresh_a_subscription() -> None:
    sub = mock_sub()
    user = mock_user(subscribed_to=[sub.uuid])

    user_repository = AsyncMock(spec=UserRepository)
    user_repository.get.return_value = user

    subscription_repository = MagicMock()
    subscription_repository.get.return_value = sub

    subscription_service = AsyncMock()
    subscription_service.get_subscription.return_value = sub

    credentials_repository = AsyncMock()
    credentials_repository.find_by_users_and_type.return_value = []

    handler = RefreshSubscriptionHandler(
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        credentials_repository=credentials_repository)

    with pytest.raises(PermissionError):
        await handler.handle(user_id=user.uuid, subscription_id=sub.uuid)

    assert subscription_service.get_subscription.call_count == 0
    assert subscription_repository.update.call_count == 0


@pytest.mark.asyncio
async def test_a_non_existing_user_cannot_refresh_a_subscription() -> None:
    sub = mock_sub()
    user = mock_user(subscribed_to=[sub.uuid])

    user_repository = AsyncMock(spec=UserRepository)
    user_repository.get.return_value = None

    subscription_repository = MagicMock()
    subscription_repository.get.return_value = sub

    subscription_service = AsyncMock()
    subscription_service.get_subscription.return_value = sub

    credentials_repository = AsyncMock()
    credentials_repository.find_by_users_and_type.return_value = []

    handler = RefreshSubscriptionHandler(
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        credentials_repository=credentials_repository)

    with pytest.raises(UserNotFoundError):
        await handler.handle(user_id=user.uuid, subscription_id=sub.uuid)

    assert subscription_service.get_subscription.call_count == 0
    assert subscription_repository.update.call_count == 0


@pytest.mark.asyncio
async def test_a_user_not_subscribed_cannot_refresh_a_subscription() -> None:
    sub = mock_sub()
    user = mock_user(subscribed_to=[])

    user_repository = AsyncMock(spec=UserRepository)
    user_repository.get.return_value = user

    subscription_repository = MagicMock()
    subscription_repository.get.return_value = sub

    subscription_service = AsyncMock()
    subscription_service.get_subscription.return_value = sub

    credentials_repository = AsyncMock()
    credentials_repository.find_by_users_and_type.return_value = []

    handler = RefreshSubscriptionHandler(
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        credentials_repository=credentials_repository)

    with pytest.raises(PermissionError):
        await handler.handle(user_id=user.uuid, subscription_id=sub.uuid)

    assert subscription_service.get_subscription.call_count == 0
    assert subscription_repository.update.call_count == 0
