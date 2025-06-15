from datetime import datetime, timezone
from ipaddress import IPv4Address
from uuid import UUID, uuid4

import pytest

from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.infrastructure.mongodb.external_credentials_repository import MongodDBExternalCredentialRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="credentials_repo", scope="session")
def fixture_item_repo(db_name: str) -> MongodDBExternalCredentialRepository:
    return MongodDBExternalCredentialRepository(
        IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")



@pytest.mark.asyncio()
async def test_exception_is_raised_if_items_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongodDBExternalCredentialRepository(
            IPv4Address("127.0.0.1"), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio()
async def test_create_credentials(credentials_repo: MongodDBExternalCredentialRepository) -> None:
    credential = ExternalServiceCredential(
        user_id=UUID("83a1ea55-d469-4f03-8d21-1d3c0096d33f"),
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test-api-key",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
    )

    stored_credentials = await credentials_repo.get(credential.user_id)
    assert len(stored_credentials) == 0

    await credentials_repo.add(credential)

    stored_credentials = await credentials_repo.get(credential.user_id)

    assert len(stored_credentials) == 1
    stored_credential = stored_credentials[0]
    assert stored_credential.user_id == credential.user_id
    assert stored_credential.credential_type == credential.credential_type
    assert stored_credential.credential_value == credential.credential_value
    assert stored_credential.created_at == credential.created_at
    assert stored_credential.updated_at == credential.updated_at


@pytest.mark.asyncio()
async def test_update_credentials(credentials_repo: MongodDBExternalCredentialRepository) -> None:
    updated_at = datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc)
    credential = ExternalServiceCredential(
        user_id=UUID("f8587b92-b872-4d19-80e6-db7d1132693e"),
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test_api_key",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=updated_at,
    )

    await credentials_repo.add(credential)

    credential.set_credential("new_test_api_key")

    await credentials_repo.update(credential)

    stored_credentials = await credentials_repo.get(credential.user_id)

    assert len(stored_credentials) == 1
    stored_credential = stored_credentials[0]
    assert stored_credential.user_id == credential.user_id
    assert stored_credential.credential_type == credential.credential_type
    assert stored_credential.credential_value == credential.credential_value
    assert stored_credential.created_at == credential.created_at
    assert stored_credential.updated_at.timestamp() > updated_at.timestamp()


@pytest.mark.asyncio()
async def test_delete_credentials(credentials_repo: MongodDBExternalCredentialRepository) -> None:
    credential = ExternalServiceCredential(
        user_id=UUID("821d0154-368e-4468-9ed0-8996e2505b73"),
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test_api_key",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
    )

    await credentials_repo.add(credential)

    await credentials_repo.delete(credential.user_id, credential.credential_type, credential.credential_value)

    stored_credentials = await credentials_repo.get(credential.user_id)

    assert len(stored_credentials) == 0


@pytest.mark.asyncio()
async def test_find_credentials_by_user_id(credentials_repo: MongodDBExternalCredentialRepository) -> None:
    credential_1 = ExternalServiceCredential(
        user_id=UUID("821d0154-368e-4468-9ed0-8996e2505b73"),
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test_api_key_1",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
    )

    credential_2 = ExternalServiceCredential(
        user_id=UUID("cbe6d4bf-3383-46ae-94ce-4150505c0e3c"),
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test_api_key_2",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
    )

    credential_3 = ExternalServiceCredential(
        user_id=credential_1.user_id,
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test_api_key_3",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
    )

    stored_credentials = await credentials_repo.get(credential_1.user_id)
    assert len(stored_credentials) == 0

    await credentials_repo.add(credential_1)
    await credentials_repo.add(credential_2)
    await credentials_repo.add(credential_3)

    stored_credentials = await credentials_repo.get(credential_1.user_id)

    assert len(stored_credentials) == 2
    credentials_values = [stored_credential.credential_value for stored_credential in stored_credentials]
    assert credential_1.credential_value in credentials_values
    assert credential_3.credential_value in credentials_values


@pytest.mark.asyncio()
async def test_find_credential_by_value_and_type(credentials_repo: MongodDBExternalCredentialRepository) -> None:
    credential = ExternalServiceCredential(
        user_id=UUID("821d0154-368e-4468-9ed0-8996e2505b73"),
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="c6114e65-1671-4c75-8b7c-0338ec965f53",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
    )

    await credentials_repo.add(credential)

    stored_credential = await credentials_repo.get_by_value_and_type(
        credential.credential_type, credential.credential_value)

    assert stored_credential is not None
    assert stored_credential.user_id == credential.user_id
    assert stored_credential.credential_type == credential.credential_type
    assert stored_credential.credential_value == credential.credential_value


@pytest.mark.asyncio()
async def test_find_non_existing_credentials_returns_none(
        credentials_repo: MongodDBExternalCredentialRepository) -> None:
    stored_credential = await credentials_repo.get_by_value_and_type(
        ExternalServiceType.YOUTUBE_API_KEY, "9c71c4bb-d429-48d3-9e19-2e1e29a5d1a0")

    assert stored_credential is None
