import argparse
import sys
from dataclasses import dataclass
from ipaddress import IPv4Address
from gunicorn.app.wsgiapp import WSGIApplication  # type: ignore
import application
from application.adapters.mongodb import run_mongodb_migrations
from application.infrastructure.fastapi.core import create_app, Handlers


@dataclass
class ApiArguments:
    port: int
    workers: int
    debug: bool
    reload: bool


@dataclass
class DbArguments:
    address: IPv4Address
    port: int
    user: str
    password: str
    name: str


@dataclass
class Arguments:
    api: ApiArguments
    db: DbArguments  # pylint: disable=invalid-name


def main():
    args = parse_args()

    run_mongodb_migrations(args.db.address, args.db.port, args.db.name, args.db.user, args.db.password)

    application.infrastructure.fastapi.core.app = create_app(Handlers(message="OK!"))
    run_server(app_path='application.infrastructure.fastapi.core:app',
               port=args.api.port, workers=args.api.workers, debug=args.api.debug, reload=args.api.reload)


def parse_args() -> Arguments:
    parser = argparse.ArgumentParser("Run the API server")
    parser.add_argument("--port", type=int, default=9000, help="Port to run the server on")
    parser.add_argument("--workers", type=int, default=4, help="Number of workers to run")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--reload", action="store_true", help="Reload server if code changes")
    parser.add_argument("--db-address", type=IPv4Address, default="127.0.0.1", help="IP address of the database")
    parser.add_argument("--db-port", type=int, default=27017, help="Port of the database")
    parser.add_argument("--db-user", type=str, default="", help="Username for the database")
    parser.add_argument("--db-password", type=str, default="", help="Password for the database")
    parser.add_argument("--db-name", type=str, default="main", help="Name of the database")
    args = parser.parse_args()

    return Arguments(
        api=ApiArguments(
            port=args.port,
            workers=args.workers,
            debug=args.debug,
            reload=args.reload
        ),
        db=DbArguments(
            address=args.db_address,
            port=args.db_port,
            user=args.db_user,
            password=args.db_password,
            name=args.db_name
        )
    )


def run_server(app_path: str, port: int, workers: int, debug: bool, reload: bool):
    sys.argv = [
        'gunicorn', app_path,
        '--workers', f"{workers}",
        '--worker-class', 'uvicorn.workers.UvicornWorker',
        '--bind', f"0.0.0.0:{port}",
        '--access-logfile', '-',
    ]
    if reload:
        sys.argv.append('--reload')
    if debug:
        sys.argv.append('--log-level')
        sys.argv.append('debug')

    app = WSGIApplication()
    app.run()


if __name__ == "__main__":
    main()
