from unittest.mock import AsyncMock
import uuid

import pytest

from linkurator_core.application.event_handler import EventHandler
from linkurator_core.domain.event import UserSubscriptionsBecameOutdatedEvent


@pytest.mark.asyncio
async def test_user_became_obsolete_event_triggers_update_user_subscriptions_handler():
    update_user_subscriptions_handler = AsyncMock()
    update_user_subscriptions_handler.handle.return_value = None
    event_handler = EventHandler(update_user_subscriptions_handler)

    await event_handler.handle(UserSubscriptionsBecameOutdatedEvent(
        event_id=uuid.UUID("416db0f0-d66f-4f47-9924-25c234615cc7"),
        user_id=uuid.UUID("5b71a7fa-0664-47b9-a28c-d43f2190c693")))

    assert update_user_subscriptions_handler.handle.call_count == 1
    assert update_user_subscriptions_handler.handle.call_args[0][0] == uuid.UUID("5b71a7fa-0664-47b9-a28c-d43f2190c693")
