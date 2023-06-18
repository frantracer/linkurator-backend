import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, List
import uuid

import sys


@dataclass
class Task:
    id: uuid.UUID
    interval_seconds: int
    callback: Callable
    latest_executed: datetime = datetime.fromtimestamp(0)


class TaskScheduler:
    def __init__(self):
        self.tasks: List[Task] = []
        self.is_running = False

    def schedule_recurring_task(self, task: Callable, interval_seconds: int, skip_first: bool = False):
        latest_executed = datetime.fromtimestamp(0)
        if skip_first:
            latest_executed = datetime.now()

        self.tasks.append(Task(id=uuid.uuid4(), interval_seconds=interval_seconds, callback=task,
                               latest_executed=latest_executed))

    async def start(self):
        self.is_running = True
        while self.is_running:
            waiting_seconds = sys.maxsize
            start_time = datetime.now()
            for task in self.tasks:
                if task.latest_executed + timedelta(seconds=task.interval_seconds) < start_time:
                    task.latest_executed = datetime.now()
                    task.callback()
                waiting_seconds = min(waiting_seconds, task.interval_seconds)

            await asyncio.sleep(waiting_seconds)

    async def stop(self):
        self.is_running = False
