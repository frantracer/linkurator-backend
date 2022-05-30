import asyncio
from typing import Any, Awaitable, Callable, List
from unittest.mock import MagicMock

import time
import pytest

from linkurator_core.application.event_bus_service import Event, EventType
from linkurator_core.infrastructure.asyncio.event_bus_service import AsyncioEventBusService


@pytest.mark.asyncio
async def test_publish_and_subscribe() -> None:
    event_bus = AsyncioEventBusService()
    dummy_function = MagicMock()
    event_bus.subscribe(EventType.ACCOUNT_CREATED, dummy_function)
    event_bus.publish(Event(EventType.ACCOUNT_CREATED, 'dummy_data'))

    results = await run_parallel(
        event_bus.start(),
        run_sequence(
            wait_until(lambda: dummy_function.call_count == 1),
            event_bus.stop()
        )
    )

    condition_was_met_in_time = results[1][0]
    assert condition_was_met_in_time


async def wait_until(condition: Callable, timeout_seconds: float = 5, check_interval_seconds: float = 1) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if condition():
            return True
        await asyncio.sleep(check_interval_seconds)
    return False


async def run_sequence(*functions: Awaitable[Any]) -> List[Any]:
    return [await function for function in functions]


async def run_parallel(*functions: Awaitable[Any]) -> List[Any]:
    return list(await asyncio.gather(*functions))
