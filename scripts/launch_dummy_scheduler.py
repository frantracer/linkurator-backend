import asyncio

from time import gmtime, strftime

from linkurator_core.infrastructure.asyncio.scheduler import TaskScheduler


async def main():
    scheduler = TaskScheduler()
    scheduler.schedule_recurring_task(
        task=lambda: print(f'{strftime("%Y-%m-%d %H:%M:%S", gmtime())} Every 5 seconds'),
        interval_seconds=5)
    scheduler.schedule_recurring_task(
        task=lambda: print(f'{strftime("%Y-%m-%d %H:%M:%S", gmtime())} Every 3 seconds'),
        interval_seconds=3)

    async def stop_scheduler():
        print(f'{strftime("%Y-%m-%d %H:%M:%S", gmtime())} Stop')
        await scheduler.stop()

    scheduler.schedule_recurring_task(
        task=lambda: asyncio.create_task(stop_scheduler()),
        interval_seconds=14,
        skip_first=True)

    await scheduler.start()


if __name__ == '__main__':
    asyncio.run(main())
