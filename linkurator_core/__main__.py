import argparse
import asyncio
from dataclasses import dataclass
import os
import signal
from typing import Optional

from uvicorn import Config, Server  # type: ignore
import uvicorn.server  # type: ignore

from linkurator_core.application.find_outdated_subscriptions_handler import FindOutdatedSubscriptionsHandler
from linkurator_core.application.find_outdated_users_handler import FindOutdatedUsersHandler
from linkurator_core.infrastructure.asyncio.scheduler import TaskScheduler
from linkurator_core.application.event_handler import EventHandler
from linkurator_core.application.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.event import SubscriptionBecameOutdatedEvent, UserSubscriptionsBecameOutdatedEvent
from linkurator_core.infrastructure.asyncio.event_bus_service import AsyncioEventBusService
from linkurator_core.infrastructure.asyncio.utils import run_parallel
from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeService
from linkurator_core.infrastructure.mongodb.repositories import run_mongodb_migrations
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository


@dataclass
class ApiArguments:
    port: int
    workers: int
    debug: bool
    reload: bool
    with_gunicorn: bool


@dataclass
class Settings:
    api: ApiArguments
    db: MongoDBSettings  # pylint: disable=invalid-name


async def main():  # pylint: disable=too-many-locals
    settings = Settings(
        api=parse_args(),
        db=MongoDBSettings()
    )

    # Migrations
    run_mongodb_migrations(settings.db.address, settings.db.port, settings.db.db_name, settings.db.user,
                           settings.db.password)

    # Repositories
    db_settings = MongoDBSettings()
    user_repository = MongoDBUserRepository(ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
                                            username=db_settings.user, password=db_settings.password)
    subscription_repository = MongoDBSubscriptionRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password
    )

    # Services
    google_client_secret_path = os.environ.get('LINKURATOR_GOOGLE_SECRET_PATH', "secrets/client_secret.json")
    google_secrets = GoogleClientSecrets(google_client_secret_path)
    account_service = GoogleAccountService(
        client_id=google_secrets.client_id,
        client_secret=google_secrets.client_secret)
    youtube_service = YoutubeService(
        google_account_service=account_service,
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        api_key=google_secrets.api_key)

    # Event bus
    loop = asyncio.get_event_loop()
    event_bus = AsyncioEventBusService()

    # Event handlers
    update_user_subscriptions = UpdateUserSubscriptionsHandler(
        youtube_service, user_repository, subscription_repository)
    find_outdated_users = FindOutdatedUsersHandler(user_repository, event_bus)
    find_outdated_subscriptions = FindOutdatedSubscriptionsHandler(subscription_repository, event_bus)
    event_handler = EventHandler(update_user_subscriptions)

    event_bus.subscribe(UserSubscriptionsBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(SubscriptionBecameOutdatedEvent, event_handler.handle)

    # Task scheduler
    scheduler = TaskScheduler()
    scheduler.schedule_recurring_task(task=find_outdated_users.handle, interval_seconds=60 * 5)
    scheduler.schedule_recurring_task(task=find_outdated_subscriptions.handle, interval_seconds=60)

    # API
    api_server = ApiServer(app_path='linkurator_core.infrastructure.fastapi.app:app',
                           port=settings.api.port, workers=settings.api.workers, debug=settings.api.debug,
                           reload=settings.api.reload, with_gunicorn=settings.api.with_gunicorn)

    for signal_type in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(
            signal_type,
            lambda: loop.create_task(run_parallel(
                api_server.stop(),
                event_bus.stop(),
                scheduler.stop()))
        )

    await run_parallel(
        event_bus.start(),
        api_server.start(),
        scheduler.start()
    )


def parse_args() -> ApiArguments:
    parser = argparse.ArgumentParser("Run the API server")
    parser.add_argument("--port", type=int, default=9000, help="Port to run the server on")
    parser.add_argument("--workers", type=int, default=4, help="Number of workers to run")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--reload", action="store_true", help="Reload server if code changes")
    parser.add_argument("--without-gunicorn", action="store_true", help="Run using only uvicorn without gunicorn")
    args = parser.parse_args()

    return ApiArguments(
        port=args.port,
        workers=args.workers,
        debug=args.debug,
        reload=args.reload,
        with_gunicorn=not args.without_gunicorn
    )


class ApiServer:
    def __init__(self, app_path: str, port: int, workers: int, debug: bool, reload: bool, with_gunicorn: bool):
        self.app_path = app_path
        self.port = port
        self.workers = workers
        self.debug = debug
        self.reload = reload
        self.with_gunicorn = with_gunicorn
        self.uvicorn_server: Optional[uvicorn.Server] = None

    async def start(self):
        if self.with_gunicorn:
            await asyncio.create_subprocess_shell(" ".join(
                ['./venv/bin/gunicorn', self.app_path,
                 '--workers', f"{self.workers}",
                 '--worker-class', 'uvicorn.workers.UvicornWorker',
                 '--bind', f"0.0.0.0:{self.port}",
                 '--access-logfile', '-',
                 '--keyfile', 'secrets/privkey.pem',
                 '--certfile', 'secrets/cert.pem',
                 '--ca-certs', 'secrets/chain.pem']))
        else:
            uvicorn.server.HANDLED_SIGNALS = []
            uvicorn_config = Config(self.app_path, port=self.port, reload=self.reload, workers=self.workers,
                                    debug=self.debug, log_level="debug" if self.debug else "info")
            self.uvicorn_server = Server(config=uvicorn_config)
            await self.uvicorn_server.serve()

    async def stop(self):
        if self.with_gunicorn:
            await asyncio.create_subprocess_shell("kill -9 $(ps aux | grep gunicorn | awk '{print $2}')")
        else:
            if self.uvicorn_server is not None:
                await self.uvicorn_server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
