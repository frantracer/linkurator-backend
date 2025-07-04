
import pytest

from linkurator_core.infrastructure.asyncio_impl.scheduler import TaskScheduler


@pytest.mark.asyncio()
async def test_scheduler() -> None:
    corroutine_2_seconds_called_times = 0
    corroutine_3_seconds_called_times = 0

    async def print_coroutine_2_seconds() -> None:
        nonlocal corroutine_2_seconds_called_times
        corroutine_2_seconds_called_times += 1

    async def print_coroutine_3_seconds() -> None:
        nonlocal corroutine_3_seconds_called_times
        corroutine_3_seconds_called_times += 1

    scheduler = TaskScheduler()
    scheduler.schedule_recurring_task(
        task=print_coroutine_2_seconds,
        interval_seconds=2)
    scheduler.schedule_recurring_task(
        task=print_coroutine_3_seconds,
        interval_seconds=3)

    async def stop_scheduler() -> None:
        await scheduler.stop()

    scheduler.schedule_recurring_task(
        task=stop_scheduler,
        interval_seconds=5,
        skip_first=True)

    await scheduler.start()

    assert corroutine_2_seconds_called_times == 3
    assert corroutine_3_seconds_called_times == 2
