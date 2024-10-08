import asyncio
import datetime
from asyncio import AbstractEventLoop
from ipaddress import IPv4Address
from typing import Generator

import pytest

from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.infrastructure.mongodb.repositories import run_mongodb_migrations


@pytest.fixture(scope="session", autouse=True)
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(name="db_name", scope="session", autouse=True)
def fixture_db_name() -> str:
    db_name = f'test-{datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}'
    run_mongodb_migrations(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")
    return db_name

PasswordChangeRequest.valid_domains = ["linkurator-test.com"]
RegistrationRequest.valid_domains = ["linkurator-test.com"]
