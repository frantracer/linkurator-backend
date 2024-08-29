from copy import copy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler, \
    MIN_REFRESH_INTERVAL_IN_SECONDS
from linkurator_core.domain.common.exceptions import SubscriptionAlreadyUpdatedError
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio
async def test_refresh_an_outdated_subscription() -> None:
    now = datetime.now(tz=timezone.utc)
    sub = mock_sub()
    sub.updated_at = now - timedelta(seconds=MIN_REFRESH_INTERVAL_IN_SECONDS + 1)

    new_sub = copy(sub)
    new_sub.name = "New Name"

    subscription_repository = InMemorySubscriptionRepository()

    await subscription_repository.add(sub)

    subscription_service = AsyncMock()
    subscription_service.get_subscription.return_value = copy(new_sub)

    handler = RefreshSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        datetime_now=lambda: now
    )

    await handler.handle(subscription_id=sub.uuid)

    updated_sub = await subscription_repository.get(sub.uuid)
    assert updated_sub is not None
    assert updated_sub.updated_at == now
    assert updated_sub.name == new_sub.name


@pytest.mark.asyncio
async def test_an_already_updated_subscription_returns_error() -> None:
    now = datetime.now(tz=timezone.utc)
    sub = mock_sub()
    sub.updated_at = now

    subscription_repository = InMemorySubscriptionRepository()
    await subscription_repository.add(sub)

    subscription_service = AsyncMock()

    handler = RefreshSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        datetime_now=lambda: now
    )

    with pytest.raises(SubscriptionAlreadyUpdatedError) as exc:
        await handler.handle(subscription_id=sub.uuid)
        assert "3600 seconds" in str(exc)
