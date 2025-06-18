from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from ipaddress import IPv4Address

from mongodb_migrations.cli import MigrationManager  # type: ignore
from mongodb_migrations.config import Configuration, Execution  # type: ignore


def run_mongodb_migrations(address: IPv4Address, port: int, db_name: str, user: str, password: str) -> None:
    mongodb_migrations_manager = MigrationManager(config=Configuration({
        "mongo_url": f"mongodb://{address}:{port}",
        "mongo_host": address,
        "mongo_port": port,
        "mongo_database": db_name,
        "mongo_username": user,
        "mongo_password": password,
        "mongo_migrations_path": f"{pathlib.Path(__file__).parent.absolute()}/migrations",
        "metastore": "database_migrations",
        "execution": Execution.MIGRATE,
        "to_datetime": datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S"),
    }))

    mongodb_migrations_manager.run()


class CollectionIsNotInitialized(Exception):
    pass
