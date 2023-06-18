import asyncio
import time
from typing import Any, Awaitable, Callable, List


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
