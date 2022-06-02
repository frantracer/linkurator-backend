import argparse
import asyncio
import signal
from dataclasses import dataclass
from typing import Optional

import uvicorn.server  # type: ignore
from uvicorn import Config, Server  # type: ignore

from linkurator_core.infrastructure.asyncio.event_bus_service import AsyncioEventBusService
from linkurator_core.infrastructure.asyncio.utils import run_parallel
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.mongodb.repositories import run_mongodb_migrations


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


async def main():
    settings = Settings(
        api=parse_args(),
        db=MongoDBSettings()
    )

    run_mongodb_migrations(settings.db.address, settings.db.port, settings.db.db_name, settings.db.user,
                           settings.db.password)

    loop = asyncio.get_event_loop()
    event_bus = AsyncioEventBusService()

    api_server = ApiServer(app_path='linkurator_core.infrastructure.fastapi.app:app',
                           port=settings.api.port, workers=settings.api.workers, debug=settings.api.debug,
                           reload=settings.api.reload, with_gunicorn=settings.api.with_gunicorn)

    for signal_type in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(
            signal_type,
            lambda: loop.create_task(run_parallel(api_server.stop(), event_bus.stop()))
        )

    await run_parallel(event_bus.start(), api_server.start())


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
