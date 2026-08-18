import asyncio
import logging

import uvicorn.server

from linkurator_core.infrastructure.config.settings import ApiSettings, ApplicationSettings
from linkurator_core.infrastructure.postgres.repositories import run_postgres_migrations


async def main(api_args: ApiSettings) -> None:
    # API
    api_server = ApiServer(
        app_path="linkurator_core.infrastructure.fastapi.app:create_app",
        host=api_args.host, port=api_args.port, workers=api_args.workers,
        debug=api_args.debug, reload=api_args.reload,
        with_gunicorn=api_args.with_gunicorn)

    await api_server.start()


class ApiServer:
    def __init__(self, app_path: str, host: str, port: int, workers: int, debug: bool, reload: bool, with_gunicorn: bool) -> None:
        self.app_path = app_path
        self.host = host
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
                 "--bind", f"{self.host}:{self.port}",
                 "--access-logfile", "-"]))

            await task.wait()
        else:
            async def run_uvicorn() -> None:
                return uvicorn.run(
                    self.app_path,
                    host=self.host,
                    port=self.port,
                    workers=self.workers,
                    log_level=logging.DEBUG if self.debug else logging.INFO,
                    reload=self.reload,
                    factory=True)

            await asyncio.create_task(run_uvicorn())


if __name__ == "__main__":
    app_settings = ApplicationSettings.from_file()

    # Migrations
    run_postgres_migrations(
        app_settings.postgres.ip_address, app_settings.postgres.port, app_settings.postgres.database,
        app_settings.postgres.user, app_settings.postgres.password)

    asyncio.run(main(app_settings.api))
