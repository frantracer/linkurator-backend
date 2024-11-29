from copy import copy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler, \
    MIN_REFRESH_INTERVAL_IN_SECONDS
from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import SubscriptionAlreadyUpdatedError, SubscriptionNotFoundError
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio
async def test_refresh_an_outdated_subscription() -> None:
    now = datetime.now(tz=timezone.utc)
    sub = mock_sub()
    sub.updated_at = now - timedelta(seconds=MIN_REFRESH_INTERVAL_IN_SECONDS + 1)
    sub.scanned_at = now - timedelta(seconds=MIN_REFRESH_INTERVAL_IN_SECONDS + 1)

    new_sub = copy(sub)
    new_sub.name = "New Name"

    subscription_repository = InMemorySubscriptionRepository()

    await subscription_repository.add(sub)

    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_service.get_subscription.return_value = copy(new_sub)

    event_bus = AsyncMock(EventBusService)

    handler = RefreshSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
        datetime_now=lambda: now
    )

    await handler.handle(subscription_id=sub.uuid)

    updated_sub = await subscription_repository.get(sub.uuid)
    assert updated_sub is not None
    assert updated_sub.updated_at == now
    assert updated_sub.name == new_sub.name

    assert len(event_bus.publish.mock_calls) == 1
    assert isinstance(event_bus.publish.mock_calls[0][1][0], SubscriptionBecameOutdatedEvent)


@pytest.mark.asyncio
async def test_an_already_updated_subscription_returns_error() -> None:
    now = datetime.now(tz=timezone.utc)
    sub = mock_sub()
    sub.updated_at = now

    subscription_repository = InMemorySubscriptionRepository()
    await subscription_repository.add(sub)

    subscription_service = AsyncMock(spec=SubscriptionService)
    event_bus = AsyncMock(spec=EventBusService)

    handler = RefreshSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
        datetime_now=lambda: now
    )

    with pytest.raises(SubscriptionAlreadyUpdatedError) as exc:
        await handler.handle(subscription_id=sub.uuid)
    assert "3600 seconds" in str(exc)


@pytest.mark.asyncio
async def test_subscription_not_found() -> None:
    subscription_repository = InMemorySubscriptionRepository()
    subscription_service = AsyncMock(spec=SubscriptionService)
    event_bus = AsyncMock(spec=EventBusService)

    handler = RefreshSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
        datetime_now=lambda: datetime.now(tz=timezone.utc)
    )

    with pytest.raises(SubscriptionNotFoundError):
        await handler.handle(subscription_id=UUID("60864001-882d-4ca3-b529-5710d86eccd8"))


@pytest.mark.asyncio
async def test_subscription_scanned_recently_does_not_publish_event() -> None:
    now = datetime.now(tz=timezone.utc)
    sub = mock_sub()
    sub.updated_at = now - timedelta(seconds=MIN_REFRESH_INTERVAL_IN_SECONDS + 1)
    sub.scanned_at = now - timedelta(seconds=MIN_REFRESH_INTERVAL_IN_SECONDS - 1)

    subscription_repository = InMemorySubscriptionRepository()
    await subscription_repository.add(sub)

    subscription_service = AsyncMock(spec=SubscriptionService)
    event_bus = AsyncMock(spec=EventBusService)

    handler = RefreshSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
        datetime_now=lambda: now
    )

    await handler.handle(subscription_id=sub.uuid)

    assert len(event_bus.publish.mock_calls) == 0
