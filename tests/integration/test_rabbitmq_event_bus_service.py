import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.common.event import SubscriptionItemsBecameOutdatedEvent
from linkurator_core.infrastructure.asyncio_impl.utils import run_parallel, run_sequence, wait_until
from linkurator_core.infrastructure.rabbitmq_event_bus import RabbitMQEventBus


@pytest.mark.asyncio()
async def test_publish_and_subscribe() -> None:
    event_bus = RabbitMQEventBus(host="localhost", port=5672, username="develop", password="develop")
    dummy_function = AsyncMock()
    event_bus.subscribe(SubscriptionItemsBecameOutdatedEvent, dummy_function)
    event = SubscriptionItemsBecameOutdatedEvent(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        subscription_id=uuid.uuid4())

    results = await run_parallel(
        event_bus.start(),
        run_sequence(
            wait_until(event_bus.is_running),
            event_bus.publish(event),
            wait_until(lambda: dummy_function.call_count == 1),
            event_bus.stop(),
        ),
    )

    condition_was_met_in_time = results[1][2]
    assert condition_was_met_in_time
