import copy
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.user import User


@pytest.mark.asyncio
async def test_update_user_subscriptions_with_a_subscription_that_is_not_registered():
    subscription_service = AsyncMock()
    sub1 = Subscription.new(
        uuid=uuid.UUID("db051fbc-3f2e-47bc-a03a-8a567e4604c9"),
        name="sub1",
        provider="myprovider",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"))
    subscription_service.get_subscriptions.return_value = [sub1]
    subscription_repository = MagicMock()
    subscription_repository.find.return_value = None
    subscription_repository.add.return_value = None

    user_repository = MagicMock()
    user = User(
        uuid=uuid.UUID("7869ee20-fda4-4ec9-88d3-c952bff2c613"),
        email="test@email.com",
        first_name="test",
        last_name="test",
        locale="en",
        avatar_url=parse_url("http://avatar.com/test.png"),
        google_refresh_token="refresh_token",
        subscription_uuids=[],
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        last_login_at=datetime.fromtimestamp(0, tz=timezone.utc),
        is_admin=False)
    user_repository.get.return_value = copy.deepcopy(user)
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
async def test_update_user_subscription_with_subscription_that_is_already_registered():
    subscription_service = AsyncMock()
    sub1 = Subscription.new(
        uuid=uuid.UUID("8c9879ec-35d1-44d5-84c1-ef1939330033"),
        name="sub1",
        provider="myprovider",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"))
    sub2 = Subscription.new(
        uuid=uuid.UUID("001db850-7edc-4fab-9e1c-6c148edfafab"),
        name="sub1",
        provider="myprovider",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"))
    subscription_service.get_subscriptions.return_value = [sub1]
    subscription_repository = MagicMock()
    subscription_repository.find.return_value = sub2
    subscription_repository.add.return_value = None

    user_repository = MagicMock()
    user = User.new(uuid=uuid.UUID("e55d0fe1-f70e-4387-9269-8e80cb747ccc"),
                    email="test@email.com",
                    first_name="test",
                    last_name="test",
                    locale="en",
                    avatar_url=parse_url("http://avatar.com/test.png"),
                    google_refresh_token="refresh_token")
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
