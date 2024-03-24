import uuid
from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.infrastructure.asyncio_impl.event_bus_service import AsyncioEventBusService
from linkurator_core.infrastructure.asyncio_impl.utils import run_parallel, run_sequence, wait_until


@pytest.mark.asyncio
async def test_publish_and_subscribe() -> None:
    event_bus = AsyncioEventBusService()
    dummy_function = AsyncMock()
    event_bus.subscribe(UserSubscriptionsBecameOutdatedEvent, dummy_function)

    results = await run_parallel(
        event_bus.start(),
        run_sequence(
            wait_until(event_bus.is_running),
            event_bus.publish(UserSubscriptionsBecameOutdatedEvent.new(uuid.uuid4())),
            wait_until(lambda: dummy_function.call_count == 1),
            event_bus.stop()
        )
    )

    condition_was_met_in_time = results[1][2]
    assert condition_was_met_in_time
