import asyncio
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, List

TaskCallback = Callable[[], Awaitable[None]]


@dataclass
class Task:
    id: uuid.UUID
    interval_seconds: int
    callback: TaskCallback
    latest_executed: datetime = datetime.fromtimestamp(0, tz=timezone.utc)


class TaskScheduler:
    def __init__(self) -> None:
        self.tasks: List[Task] = []
        self.is_running = False

    def schedule_recurring_task(self, task: TaskCallback, interval_seconds: int, skip_first: bool = False) -> None:
        latest_executed = datetime.fromtimestamp(0, tz=timezone.utc)
        if skip_first:
            latest_executed = datetime.now(timezone.utc)

        new_task = Task(id=uuid.uuid4(),
                        interval_seconds=interval_seconds,
                        callback=task,
                        latest_executed=latest_executed)
        self.tasks.append(new_task)

    async def start(self) -> None:
        self.is_running = True
        while self.is_running:
            waiting_seconds = sys.maxsize
            start_time = datetime.now(timezone.utc)
            for task in self.tasks:
                remaining_time = task.latest_executed + timedelta(seconds=task.interval_seconds) - start_time
                if task.latest_executed + timedelta(seconds=task.interval_seconds) <= start_time:
                    task.latest_executed = datetime.now(timezone.utc)
                    await task.callback()
                waiting_seconds = min(waiting_seconds, int(remaining_time.total_seconds()))

            await asyncio.sleep(waiting_seconds)

    async def stop(self) -> None:
        self.is_running = False
