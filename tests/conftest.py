import datetime
from ipaddress import IPv4Address

import pytest

from linkurator_core.infrastructure.mongodb.repositories import run_mongodb_migrations


@pytest.fixture(name="db_name", scope="session", autouse=True)
def fixture_db_name() -> str:
    db_name = f'test-{datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}'
    run_mongodb_migrations(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")
    return db_name
