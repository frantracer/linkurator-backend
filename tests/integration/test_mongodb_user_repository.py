from datetime import datetime, timezone
from ipaddress import IPv4Address
from unittest import mock
from unittest.mock import MagicMock
import uuid

from math import floor
import pytest

from linkurator_core.common import utils
from linkurator_core.domain.user import User
from linkurator_core.domain.user_repository import EmailAlreadyInUse
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUser, MongoDBUserRepository


@pytest.fixture(name="user_repo", scope="session")
def fixture_user_repo(db_name) -> MongoDBUserRepository:
    return MongoDBUserRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


def test_exception_is_raised_if_users_collection_is_not_created():
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        MongoDBUserRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")


def test_add_user_to_mongodb(user_repo: MongoDBUserRepository):
    user = User.new(
        first_name="test",
        last_name="test",
        email="test@test.com",
        locale="en",
        avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
        uuid=uuid.UUID("679c6db9-a54e-4947-b825-57a96fb5f599"),
        google_refresh_token="token",
        is_admin=True)

    user_repo.add(user)
    the_user = user_repo.get(user.uuid)

    assert the_user is not None
    assert the_user.first_name == user.first_name
    assert the_user.email == user.email
    assert the_user.uuid == user.uuid
    assert the_user.locale == user.locale
    assert the_user.avatar_url == user.avatar_url
    assert the_user.google_refresh_token == user.google_refresh_token
    assert int(the_user.created_at.timestamp() * 100) == floor(user.created_at.timestamp() * 100)
    assert int(the_user.updated_at.timestamp() * 100) == floor(user.updated_at.timestamp() * 100)
    assert int(the_user.scanned_at.timestamp() * 100) == floor(user.scanned_at.timestamp() * 100)
    assert int(the_user.last_login_at.timestamp() * 100) == floor(user.last_login_at.timestamp() * 100)
    assert the_user.is_admin


def test_get_user_that_does_not_exist(user_repo: MongoDBUserRepository):
    the_user = user_repo.get(uuid.UUID("c04c2880-6376-4fe1-a0bf-eac1ae0801ad"))

    assert the_user is None


def test_get_user_with_invalid_format_raises_an_exception(user_repo: MongoDBUserRepository):
    user_dict = dict(MongoDBUser(uuid=uuid.UUID("449e3bee-6f9b-4cbc-8a09-64a6fcface96"),
                                 first_name="test",
                                 last_name="test",
                                 email="test@email.com",
                                 locale="en",
                                 avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                                 created_at=datetime.now(timezone.utc),
                                 updated_at=datetime.now(timezone.utc),
                                 last_login_at=datetime.now(timezone.utc),
                                 google_refresh_token="token"))
    user_dict['uuid'] = 'invalid_uuid'
    user_collection_mock = MagicMock()
    user_collection_mock.find_one = MagicMock(return_value=user_dict)
    with mock.patch.object(MongoDBUserRepository, '_user_collection', return_value=user_collection_mock):
        with pytest.raises(ValueError):
            user_repo.get(uuid.UUID("c0d59790-bb68-415b-9be5-79c3088aada0"))


def test_delete_user(user_repo: MongoDBUserRepository):
    user = User.new(first_name="test",
                    last_name="test",
                    email="test_1@test.com",
                    locale="en",
                    avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                    uuid=uuid.UUID("1006a7a9-4c12-4475-9c4a-7c0f6c9f8eb3"),
                    google_refresh_token="token")

    user_repo.add(user)
    the_user = user_repo.get(user.uuid)
    assert the_user is not None

    user_repo.delete(user.uuid)
    deleted_user = user_repo.get(user.uuid)
    assert deleted_user is None


def test_update_user(user_repo: MongoDBUserRepository):
    user = User.new(first_name="test",
                    last_name="test",
                    email="update_1@email.com",
                    locale="en",
                    avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                    uuid=uuid.UUID("0a634935-2fca-4103-b036-94dfa5d3eeaa"),
                    google_refresh_token="token")

    user_repo.add(user)
    the_user = user_repo.get(user.uuid)
    assert the_user is not None

    user.first_name = "updated"
    user_repo.update(user)
    updated_user = user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.first_name == user.first_name


def test_get_user_by_email(user_repo: MongoDBUserRepository):
    user = User.new(first_name="test",
                    last_name="test",
                    email="sample_1@test.com",
                    locale="en",
                    avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                    uuid=uuid.UUID("bb43a19d-cb28-4634-8ca7-4a5f6539678c"),
                    google_refresh_token="token")

    user_repo.add(user)
    the_user = user_repo.get_by_email(user.email)

    assert the_user is not None
    assert the_user.uuid == user.uuid


def test_the_email_is_unique(user_repo: MongoDBUserRepository):
    user_1 = User.new(first_name="test",
                      last_name="test",
                      email="sample_2@test.com",
                      locale="en",
                      avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                      uuid=uuid.UUID("18244f86-75ea-4420-abcb-3552a51289ea"),
                      google_refresh_token="token")
    user_2 = User.new(first_name="test",
                      last_name="test",
                      email="sample_2@test.com",
                      locale="en",
                      avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                      uuid=uuid.UUID("b310f930-0f0b-467e-b746-0ed1c11449b8"),
                      google_refresh_token="token")

    user_repo.add(user_1)

    with pytest.raises(EmailAlreadyInUse):
        user_repo.add(user_2)


def test_find_latest_scan(user_repo: MongoDBUserRepository):
    user1 = User.new(first_name="test",
                     last_name="test",
                     email="c2d73a23@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("c2d73a23-217b-4985-a4f6-7f5828daa964"),
                     google_refresh_token="token")
    user1.scanned_at = datetime.fromisoformat("2020-01-01T00:00:00+00:00")

    user2 = User.new(first_name="test",
                     last_name="test",
                     email="4cef3a68@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("4cef3a68-9ec0-48e8-a6de-a56dd3ba1adf"),
                     google_refresh_token="token")
    user2.scanned_at = datetime.fromisoformat("2020-01-02T00:00:00+00:00")

    users_first_call = user_repo.find_latest_scan_before(datetime.fromisoformat("2020-01-01T12:00:00+00:00"))

    user_repo.add(user1)
    user_repo.add(user2)

    users_second_call = user_repo.find_latest_scan_before(datetime.fromisoformat("2020-01-01T12:00:00+00:00"))

    assert len(users_second_call) - len(users_first_call) == 1
    assert user1.uuid in [user.uuid for user in users_second_call]
