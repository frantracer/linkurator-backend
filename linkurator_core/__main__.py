import argparse
import asyncio
import logging
from dataclasses import dataclass

import uvicorn.server

from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.mongodb.repositories import run_mongodb_migrations


@dataclass
class ApiArguments:
    port: int
    workers: int
    debug: bool
    reload: bool
    with_gunicorn: bool


async def main() -> None:
    api_settings = parse_args()
    app_settings = ApplicationSettings.from_file()

    # Migrations
    run_mongodb_migrations(
        app_settings.mongodb.address, app_settings.mongodb.port, app_settings.mongodb.db_name,
        app_settings.mongodb.user, app_settings.mongodb.password)

    # API
    api_server = ApiServer(app_path="linkurator_core.infrastructure.fastapi.app:create_app",
                           port=api_settings.port, workers=api_settings.workers, debug=api_settings.debug,
                           reload=api_settings.reload, with_gunicorn=api_settings.with_gunicorn)

    await api_server.start()


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
        with_gunicorn=not args.without_gunicorn,
    )


class ApiServer:
    def __init__(self, app_path: str, port: int, workers: int, debug: bool, reload: bool, with_gunicorn: bool) -> None:
        self.app_path = app_path
        self.port = port
        self.workers = workers
        self.debug = debug
        self.reload = reload
        self.with_gunicorn = with_gunicorn

    async def start(self) -> None:
        if self.with_gunicorn:
            task = await asyncio.create_subprocess_shell(" ".join(
                [".venv/bin/gunicorn", self.app_path,
                 "--workers", f"{self.workers}",
                 "--worker-class", "uvicorn.workers.UvicornWorker",
                 "--bind", f"0.0.0.0:{self.port}",
                 "--access-logfile", "-"]))

            await task.wait()
        else:
            async def run_uvicorn() -> None:
                return uvicorn.run(
                    self.app_path,
                    host="127.0.0.1",
                    port=self.port,
                    workers=self.workers,
                    log_level=logging.DEBUG if self.debug else logging.INFO,
                    reload=self.reload,
                    factory=True)

            await asyncio.create_task(run_uvicorn())


if __name__ == "__main__":
    asyncio.run(main())
