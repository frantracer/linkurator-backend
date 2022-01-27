import datetime
import ipaddress
import uuid
from math import floor

import pytest

from application.adapters.mongodb import MongoDBUserRepository
from application.domain.model import User


@pytest.fixture(name="user_repo")
def fixture_user_repo() -> MongoDBUserRepository:
    db_name = f'test-{datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}'
    repo = MongoDBUserRepository(ipaddress.IPv4Address('127.0.0.1'), 27017, db_name)
    return repo


def test_add_user_to_mongodb(user_repo: MongoDBUserRepository):
    user = User(name="test", email="test@test.com", uuid=uuid.UUID("679c6db9-a54e-4947-b825-57a96fb5f599"),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())

    user_repo.add(user)
    the_user = user_repo.get(user.uuid)

    assert the_user is not None
    assert the_user.name == user.name
    assert the_user.email == user.email
    assert the_user.uuid == user.uuid
    assert int(the_user.created_at.timestamp() * 100) == floor(user.created_at.timestamp() * 100)
    assert int(the_user.updated_at.timestamp() * 100) == floor(user.updated_at.timestamp() * 100)


def test_get_user_that_does_not_exist(user_repo: MongoDBUserRepository):
    the_user = user_repo.get(uuid.UUID("c04c2880-6376-4fe1-a0bf-eac1ae0801ad"))

    assert the_user is None


def test_delete_user(user_repo: MongoDBUserRepository):
    user = User(name="test", email="test@test.com", uuid=uuid.UUID("1006a7a9-4c12-4475-9c4a-7c0f6c9f8eb3"),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())

    user_repo.add(user)
    the_user = user_repo.get(user.uuid)
    assert the_user is not None

    user_repo.delete(user.uuid)
    deleted_user = user_repo.get(user.uuid)
    assert deleted_user is None
