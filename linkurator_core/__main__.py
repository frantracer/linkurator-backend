import argparse
import asyncio
from dataclasses import dataclass

from uvicorn import Config, Server  # type: ignore

from linkurator_core.infrastructure.asyncio.event_bus_service import AsyncioEventBusService
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

    event_bus = AsyncioEventBusService()
    api_server = run_server(app_path='linkurator_core.infrastructure.fastapi.app:app',
                            port=settings.api.port, workers=settings.api.workers, debug=settings.api.debug,
                            reload=settings.api.reload, with_gunicorn=settings.api.with_gunicorn)
    await asyncio.gather(api_server, event_bus.start())


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


async def run_server(app_path: str, port: int, workers: int, debug: bool, reload: bool, with_gunicorn: bool):
    if with_gunicorn:
        await asyncio.create_subprocess_shell(" ".join(
            ['./venv/bin/gunicorn', app_path,
             '--workers', f"{workers}",
             '--worker-class', 'uvicorn.workers.UvicornWorker',
             '--bind', f"0.0.0.0:{port}",
             '--access-logfile', '-',
             '--keyfile', 'secrets/privkey.pem',
             '--certfile', 'secrets/cert.pem',
             '--ca-certs', 'secrets/chain.pem']))
    else:
        uvicorn_config = Config(app_path, port=port, reload=reload, workers=workers, debug=debug,
                                log_level="debug" if debug else "info")
        uvicorn_server = Server(config=uvicorn_config)
        await uvicorn_server.serve()


if __name__ == "__main__":
    asyncio.run(main())
