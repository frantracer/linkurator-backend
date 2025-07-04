import datetime
import uuid
from unittest.mock import AsyncMock, call

import pytest

from linkurator_core.application.common.event_handler import EventHandler
from linkurator_core.domain.common.event import (
    SubscriptionBecameOutdatedEvent,
    SubscriptionItemsBecameOutdatedEvent,
    UserRegisteredEvent,
    UserRegisterRequestSentEvent,
)


def dummy_event_handler() -> EventHandler:
    return EventHandler(
        update_user_subscriptions_handler=AsyncMock(),
        update_subscription_items_handler=AsyncMock(),
        update_subscription_handler=AsyncMock(),
        refresh_items_handler=AsyncMock(),
        send_validate_new_user_email=AsyncMock(),
        send_welcome_email=AsyncMock(),
    )


@pytest.mark.asyncio()
async def test_subscription_items_became_obsolete_event_triggers_update_subscriptions_items_handler() -> None:
    update_subscription_items_handler = AsyncMock()
    update_subscription_items_handler.handle.return_value = None
    event_handler = dummy_event_handler()
    event_handler.update_subscription_items_handler = update_subscription_items_handler

    await event_handler.handle(SubscriptionItemsBecameOutdatedEvent(
        id=uuid.UUID("f71fcaa6-0baf-43f3-863d-292bea2989e9"),
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        subscription_id=uuid.UUID("4d00e658-2947-4781-a045-691f0ef57831")))

    handle_calls = update_subscription_items_handler.handle.call_args_list
    assert len(handle_calls) == 1
    assert handle_calls[0] == call(uuid.UUID("4d00e658-2947-4781-a045-691f0ef57831"))


@pytest.mark.asyncio()
async def test_subscription_became_obsolete_event_triggers_update_subscription_handler() -> None:
    update_subscription_handler = AsyncMock()
    update_subscription_handler.handle.return_value = None
    event_handler = dummy_event_handler()
    event_handler.update_subscription_handler = update_subscription_handler

    await event_handler.handle(SubscriptionBecameOutdatedEvent(
        id=uuid.UUID("1f1aebb5-51ba-4a08-9b63-697ea49c5512"),
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        subscription_id=uuid.UUID("4d00e658-2947-4781-a045-691f0ef57831")))

    handle_calls = update_subscription_handler.handle.call_args_list
    assert len(handle_calls) == 1
    assert handle_calls[0] == call(uuid.UUID("4d00e658-2947-4781-a045-691f0ef57831"))


@pytest.mark.asyncio()
async def test_new_registration_request_event_triggers_validate_the_new_user_email_handler() -> None:
    send_validate_new_user_email = AsyncMock()
    send_validate_new_user_email.handle.return_value = None
    event_handler = dummy_event_handler()
    event_handler.send_validate_new_user_email = send_validate_new_user_email

    await event_handler.handle(UserRegisterRequestSentEvent.new(
        request_uuid=uuid.UUID("4a814f72-28bb-4e75-a9ab-8e3d9715a29a")))

    handle_calls = send_validate_new_user_email.handle.call_args_list
    assert len(handle_calls) == 1
    assert handle_calls[0] == call(uuid.UUID("4a814f72-28bb-4e75-a9ab-8e3d9715a29a"))


@pytest.mark.asyncio()
async def test_new_registered_user_event_triggers_send_welcome_email_handler() -> None:
    send_welcome_email = AsyncMock()
    send_welcome_email.handle.return_value = None
    event_handler = dummy_event_handler()
    event_handler.send_welcome_email = send_welcome_email

    await event_handler.handle(UserRegisteredEvent.new(
        user_id=uuid.UUID("e3b84e67-11d9-425d-936e-6eb64689f17d")))

    handle_calls = send_welcome_email.handle.call_args_list
    assert len(handle_calls) == 1
    assert handle_calls[0] == call(uuid.UUID("e3b84e67-11d9-425d-936e-6eb64689f17d"))
