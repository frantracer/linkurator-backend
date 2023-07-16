from unittest.mock import AsyncMock
import uuid

import pytest

from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.infrastructure.asyncio.event_bus_service import AsyncioEventBusService
from linkurator_core.infrastructure.asyncio.utils import run_parallel, run_sequence, wait_until


@pytest.mark.asyncio
async def test_publish_and_subscribe() -> None:
    event_bus = AsyncioEventBusService()
    dummy_function = AsyncMock()
    event_bus.subscribe(UserSubscriptionsBecameOutdatedEvent, dummy_function)
    event_bus.publish(UserSubscriptionsBecameOutdatedEvent(uuid.uuid4(), uuid.uuid4()))

    results = await run_parallel(
        event_bus.start(),
        run_sequence(
            wait_until(lambda: dummy_function.call_count == 1),
            event_bus.stop()
        )
    )

    condition_was_met_in_time = results[1][0]
    assert condition_was_met_in_time
