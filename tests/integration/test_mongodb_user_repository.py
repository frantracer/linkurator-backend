import uuid
from datetime import datetime, timezone
from ipaddress import IPv4Address
from math import floor
from unittest import mock
from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.common import utils
from linkurator_core.domain.users.user import User, Username
from linkurator_core.domain.users.user_repository import EmailAlreadyInUse
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUser, MongoDBUserRepository


@pytest.fixture(name="user_repo", scope="session")
def fixture_user_repo(db_name: str) -> MongoDBUserRepository:
    return MongoDBUserRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio
async def test_exception_is_raised_if_users_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBUserRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio
async def test_add_user_to_mongodb(user_repo: MongoDBUserRepository) -> None:
    user = User.new(
        first_name="test",
        last_name="test",
        username=Username("testtest"),
        email="test@test.com",
        locale="en",
        avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
        uuid=uuid.UUID("679c6db9-a54e-4947-b825-57a96fb5f599"),
        google_refresh_token="token",
        is_admin=True,
        curators={uuid.UUID("0453e71a-2754-4a27-9ac3-d5e2a9768e8a")},
        followed_topics={uuid.UUID("6c190535-dcff-4be7-8497-dd5b14b400dc")}
    )

    await user_repo.add(user)
    the_user = await user_repo.get(user.uuid)

    assert the_user is not None
    assert the_user.first_name == user.first_name
    assert the_user.last_name == user.last_name
    assert the_user.username == user.username
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
    assert the_user.curators == user.curators
    assert the_user.get_followed_topics() == user.get_followed_topics()


@pytest.mark.asyncio
async def test_get_user_that_does_not_exist(user_repo: MongoDBUserRepository) -> None:
    the_user = await user_repo.get(uuid.UUID("c04c2880-6376-4fe1-a0bf-eac1ae0801ad"))

    assert the_user is None


@pytest.mark.asyncio
async def test_get_user_with_invalid_format_raises_an_exception(user_repo: MongoDBUserRepository) -> None:
    user_dict = MongoDBUser(uuid=uuid.UUID("449e3bee-6f9b-4cbc-8a09-64a6fcface96"),
                            first_name="test",
                            last_name="test",
                            username="test",
                            email="test@email.com",
                            locale="en",
                            avatar_url="https://avatars.com/avatar.png",
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                            last_login_at=datetime.now(timezone.utc),
                            google_refresh_token="token"
                            ).model_dump()
    user_dict['uuid'] = 'invalid_uuid'
    user_collection_mock = AsyncMock()
    user_collection_mock.find_one = AsyncMock(return_value=user_dict)
    with mock.patch.object(MongoDBUserRepository, '_collection', return_value=user_collection_mock):
        with pytest.raises(ValueError):
            await user_repo.get(uuid.UUID("c0d59790-bb68-415b-9be5-79c3088aada0"))


@pytest.mark.asyncio
async def test_delete_user(user_repo: MongoDBUserRepository) -> None:
    user = User.new(first_name="test",
                    last_name="test",
                    username=Username("test_1"),
                    email="test_1@test.com",
                    locale="en",
                    avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                    uuid=uuid.UUID("1006a7a9-4c12-4475-9c4a-7c0f6c9f8eb3"),
                    google_refresh_token="token")

    await user_repo.add(user)
    the_user = await user_repo.get(user.uuid)
    assert the_user is not None

    await user_repo.delete(user.uuid)
    deleted_user = await user_repo.get(user.uuid)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_update_user(user_repo: MongoDBUserRepository) -> None:
    user = User.new(first_name="test",
                    last_name="test",
                    username=Username("update_1"),
                    email="update_1@email.com",
                    locale="en",
                    avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                    uuid=uuid.UUID("0a634935-2fca-4103-b036-94dfa5d3eeaa"),
                    google_refresh_token="token")

    await user_repo.add(user)
    the_user = await user_repo.get(user.uuid)
    assert the_user is not None

    user.first_name = "updated"
    await user_repo.update(user)
    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.first_name == user.first_name


@pytest.mark.asyncio
async def test_get_user_by_email(user_repo: MongoDBUserRepository) -> None:
    user = User.new(first_name="test",
                    last_name="test",
                    username=Username("sample_1"),
                    email="sample_1@test.com",
                    locale="en",
                    avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                    uuid=uuid.UUID("bb43a19d-cb28-4634-8ca7-4a5f6539678c"),
                    google_refresh_token="token")

    await user_repo.add(user)
    the_user = await user_repo.get_by_email(user.email)

    assert the_user is not None
    assert the_user.uuid == user.uuid


@pytest.mark.asyncio
async def test_the_email_is_unique(user_repo: MongoDBUserRepository) -> None:
    user_1 = User.new(
        first_name="test",
        last_name="test",
        username=Username("sample_2"),
        email="sample_2@test.com",
        locale="en",
        avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
        uuid=uuid.UUID("18244f86-75ea-4420-abcb-3552a51289ea"),
        google_refresh_token="token")
    user_2 = User.new(
        first_name="test",
        last_name="test",
        username=Username("sample_2_bis"),
        email="sample_2@test.com",
        locale="en",
        avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
        uuid=uuid.UUID("b310f930-0f0b-467e-b746-0ed1c11449b8"),
        google_refresh_token="token")

    await user_repo.add(user_1)

    with pytest.raises(EmailAlreadyInUse):
        await user_repo.add(user_2)


@pytest.mark.asyncio
async def test_find_latest_scan(user_repo: MongoDBUserRepository) -> None:
    user1 = User.new(first_name="test",
                     last_name="test",
                     username=Username("c2d73a23"),
                     email="c2d73a23@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("c2d73a23-217b-4985-a4f6-7f5828daa964"),
                     google_refresh_token="token")
    user1.scanned_at = datetime.fromisoformat("2020-01-01T00:00:00+00:00")

    user2 = User.new(first_name="test",
                     last_name="test",
                     username=Username("4cef3a68"),
                     email="4cef3a68@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("4cef3a68-9ec0-48e8-a6de-a56dd3ba1adf"),
                     google_refresh_token="token")
    user2.scanned_at = datetime.fromisoformat("2020-01-02T00:00:00+00:00")

    users_first_call = await user_repo.find_latest_scan_before(datetime.fromisoformat("2020-01-01T12:00:00+00:00"))

    await user_repo.add(user1)
    await user_repo.add(user2)

    users_second_call = await user_repo.find_latest_scan_before(datetime.fromisoformat("2020-01-01T12:00:00+00:00"))

    assert len(users_second_call) - len(users_first_call) == 1
    assert user1.uuid in [user.uuid for user in users_second_call]


@pytest.mark.asyncio
async def test_find_users_by_subscription(user_repo: MongoDBUserRepository) -> None:
    user1 = User.new(first_name="test",
                     last_name="test",
                     username=Username("9cca4ef4"),
                     email="9cca4ef4@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("9cca4ef4-3940-4527-8789-f76673a3842b"),
                     google_refresh_token="token",
                     subscription_uuids={uuid.UUID("902e771b-4ff2-4c0a-ace2-06aab6d27e17")})

    user2 = User.new(first_name="test",
                     last_name="test",
                     username=Username("021991aa"),
                     email="021991aa@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("021991aa-f9da-4935-bf34-7ffc805e1465"),
                     google_refresh_token="token",
                     subscription_uuids={uuid.UUID("7395039e-6816-49fb-a303-706caad02673")})

    await user_repo.add(user1)
    await user_repo.add(user2)

    users = await user_repo.find_users_subscribed_to_subscription(uuid.UUID("902e771b-4ff2-4c0a-ace2-06aab6d27e17"))

    assert len(users) == 1
    assert user1.uuid in [user.uuid for user in users]


@pytest.mark.asyncio
async def test_find_users_by_subscription_empty(user_repo: MongoDBUserRepository) -> None:
    user = User.new(first_name="test",
                    last_name="test",
                    username=Username("cb7b18dc"),
                    email="cb7b18dc@email.com",
                    locale="en",
                    avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                    uuid=uuid.UUID("cb7b18dc-15d8-46b4-bce6-7214fa1a988b"),
                    google_refresh_token="token",
                    subscription_uuids={uuid.UUID("9373199d-118d-4493-a6ea-878bf0647ecb")})

    await user_repo.add(user)

    users = await user_repo.find_users_subscribed_to_subscription(uuid.UUID("225b802f-af94-4c47-870a-f51bbecc5610"))

    assert len(users) == 0


@pytest.mark.asyncio
async def test_get_user_by_username(user_repo: MongoDBUserRepository) -> None:
    user1 = User.new(first_name="test",
                     last_name="test",
                     username=Username("eeff7d5b"),
                     email="eeff7d5b@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("eeff7d5b-6c6a-442d-86d4-0140c4212116"),
                     google_refresh_token="token",
                     subscription_uuids=set())

    user2 = User.new(first_name="test",
                     last_name="test",
                     username=Username("c932c023"),
                     email="c932c023@email.com",
                     locale="en",
                     avatar_url=utils.parse_url("https://avatars.com/avatar.png"),
                     uuid=uuid.UUID("c932c023-730f-4448-9022-854e64cff9ee"),
                     google_refresh_token="token",
                     subscription_uuids=set())

    await user_repo.add(user1)
    await user_repo.add(user2)

    found_user = await user_repo.get_by_username(Username("eeff7d5b"))
    assert found_user is not None
    assert found_user.uuid == user1.uuid


@pytest.mark.asyncio
async def test_get_non_existing_username(user_repo: MongoDBUserRepository) -> None:
    assert await user_repo.get_by_username(Username("non_existent")) is None
