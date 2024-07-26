import uuid
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest

from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.common.exceptions import InvalidCredentialError
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio
async def test_update_user_subscriptions_with_a_subscription_that_is_not_registered() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    sub1 = Subscription.new(
        uuid=uuid.UUID("db051fbc-3f2e-47bc-a03a-8a567e4604c9"),
        name="sub1",
        provider=SubscriptionProvider.YOUTUBE,
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"))
    subscription_service.get_subscriptions.return_value = [sub1]
    subscription_repository = MagicMock(spec=SubscriptionRepository)
    subscription_repository.find.return_value = None
    subscription_repository.add.return_value = None

    user_repository = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repository.get.return_value = deepcopy(user)
    user_repository.update.return_value = None

    handler = UpdateUserSubscriptionsHandler(subscription_service=subscription_service,
                                             user_repository=user_repository,
                                             subscription_repository=subscription_repository)
    await handler.handle(user.uuid)

    assert subscription_service.get_subscriptions.call_count == 1
    assert subscription_service.get_subscriptions.call_args[0][0] == user.uuid
    assert subscription_repository.find.call_count == 1
    assert subscription_repository.add.call_count == 1
    assert subscription_repository.add.call_args[0][0] == sub1
    assert user_repository.update.call_count == 1
    user_input: User = user_repository.update.call_args[0][0]
    assert user_input.uuid == user.uuid
    assert user_input.subscription_uuids[0] == sub1.uuid
    assert user_input.scanned_at > user.scanned_at


@pytest.mark.asyncio
async def test_update_user_subscription_with_subscription_that_is_already_registered() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    sub1 = Subscription.new(
        uuid=uuid.UUID("8c9879ec-35d1-44d5-84c1-ef1939330033"),
        name="sub1",
        provider=SubscriptionProvider.YOUTUBE,
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"))
    sub2 = Subscription.new(
        uuid=uuid.UUID("001db850-7edc-4fab-9e1c-6c148edfafab"),
        name="sub1",
        provider=SubscriptionProvider.YOUTUBE,
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"))
    subscription_service.get_subscriptions.return_value = [sub1]
    subscription_repository = MagicMock(spec=SubscriptionRepository)
    subscription_repository.find.return_value = sub2
    subscription_repository.add.return_value = None

    user_repository = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repository.get.return_value = user
    user_repository.update.return_value = None

    handler = UpdateUserSubscriptionsHandler(subscription_service=subscription_service,
                                             user_repository=user_repository,
                                             subscription_repository=subscription_repository)
    await handler.handle(user.uuid)

    assert subscription_service.get_subscriptions.call_count == 1
    assert subscription_service.get_subscriptions.call_args[0][0] == user.uuid
    assert subscription_repository.find.call_count == 1
    assert subscription_repository.add.call_count == 0
    assert user_repository.update.call_count == 1
    user_input: User = user_repository.update.call_args[0][0]
    assert user_input.uuid == user.uuid
    assert user_input.subscription_uuids[0] == sub2.uuid


@pytest.mark.asyncio
async def test_update_subscriptions_for_non_existing_user_does_nothing() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_repository = MagicMock(spec=SubscriptionRepository)
    user_repository = MagicMock(spec=UserRepository)
    user_repository.get.return_value = None

    handler = UpdateUserSubscriptionsHandler(subscription_service=subscription_service,
                                             user_repository=user_repository,
                                             subscription_repository=subscription_repository)
    user_id = uuid.UUID("3577da9f-2d85-4475-9aaf-5f38cd01bc2a")
    await handler.handle(user_id)

    assert subscription_service.get_subscriptions.call_count == 0
    assert user_repository.update.call_count == 0
    assert user_repository.get.call_count == 1
    assert user_repository.get.call_args[0][0] == user_id


@pytest.mark.asyncio
async def test_update_subscriptions_for_user_with_invalid_refresh_token_only_updates_scanned_at() -> None:
    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_service.get_subscriptions.side_effect = InvalidCredentialError("Invalid refresh token")
    subscription_repository = MagicMock(spec=SubscriptionRepository)
    user_repository = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repository.get.return_value = deepcopy(user)

    handler = UpdateUserSubscriptionsHandler(subscription_service=subscription_service,
                                             user_repository=user_repository,
                                             subscription_repository=subscription_repository)
    await handler.handle(user.uuid)

    assert subscription_service.get_subscriptions.call_count == 1
    assert user_repository.update.call_count == 1
    user_input: User = user_repository.update.call_args[0][0]
    assert user_input.uuid == user.uuid
    assert user_input.subscription_uuids == user.subscription_uuids
    assert user_input.scanned_at > user.scanned_at
