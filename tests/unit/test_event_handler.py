from unittest.mock import AsyncMock, MagicMock, call
import uuid

import pytest

from linkurator_core.application.common.event_handler import EventHandler
from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent, UserSubscriptionsBecameOutdatedEvent


@pytest.mark.asyncio
async def test_user_became_obsolete_event_triggers_update_user_subscriptions_handler() -> None:
    update_user_subscriptions_handler = AsyncMock()
    update_user_subscriptions_handler.handle.return_value = None
    event_handler = EventHandler(
        update_user_subscriptions_handler=update_user_subscriptions_handler,
        update_subscription_items_handler=MagicMock(),
        refresh_items_handler=MagicMock())

    await event_handler.handle(UserSubscriptionsBecameOutdatedEvent(
        event_id=uuid.UUID("416db0f0-d66f-4f47-9924-25c234615cc7"),
        user_id=uuid.UUID("5b71a7fa-0664-47b9-a28c-d43f2190c693")))

    handle_calls = update_user_subscriptions_handler.handle.call_args_list
    assert len(handle_calls) == 1
    assert handle_calls[0] == call(uuid.UUID("5b71a7fa-0664-47b9-a28c-d43f2190c693"))


@pytest.mark.asyncio
async def test_subscription_became_obsolete_event_triggers_update_subscriptions_items_handler() -> None:
    update_subscription_items_handler = AsyncMock()
    update_subscription_items_handler.handle.return_value = None
    event_handler = EventHandler(
        update_user_subscriptions_handler=MagicMock(),
        update_subscription_items_handler=update_subscription_items_handler,
        refresh_items_handler=MagicMock())

    await event_handler.handle(SubscriptionBecameOutdatedEvent(
        event_id=uuid.UUID("f71fcaa6-0baf-43f3-863d-292bea2989e9"),
        subscription_id=uuid.UUID("4d00e658-2947-4781-a045-691f0ef57831")))

    handle_calls = update_subscription_items_handler.handle.call_args_list
    assert len(handle_calls) == 1
    assert handle_calls[0] == call(uuid.UUID("4d00e658-2947-4781-a045-691f0ef57831"))
