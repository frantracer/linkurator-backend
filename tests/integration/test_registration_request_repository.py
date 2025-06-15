from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import AnyUrl

from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository
from linkurator_core.infrastructure.in_memory.registration_request_repository import (
    InMemoryRegistrationRequestRepository,
)
from linkurator_core.infrastructure.mongodb.registration_request_repository import MongoDBRegistrationRequestRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="reg_request_repo", scope="session", params=["mongodb", "in_memory"])
def fixture_topic_repo(db_name: str, request: Any) -> RegistrationRequestRepository:
    if request.param == "in_memory":
        return InMemoryRegistrationRequestRepository()
    return MongoDBRegistrationRequestRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio()
async def test_exception_is_raised_if_registration_request_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBRegistrationRequestRepository(
            IPv4Address("127.0.0.1"), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio()
async def test_add_request(reg_request_repo: RegistrationRequestRepository) -> None:
    request = RegistrationRequest(
        uuid=UUID("647e918e-658f-4372-9da5-98c2354e287f"),
        user=mock_user(),
        valid_until=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
    )

    await reg_request_repo.add_request(request)
    the_request = await reg_request_repo.get_request(request.uuid)

    assert the_request is not None
    assert the_request.uuid == request.uuid


@pytest.mark.asyncio()
async def test_get_request_that_does_not_exist(reg_request_repo: RegistrationRequestRepository) -> None:
    the_request = await reg_request_repo.get_request(UUID("f4d73e72-7d36-4bd2-8a5b-79c631d177df"))

    assert the_request is None


@pytest.mark.asyncio()
async def test_delete_request(reg_request_repo: RegistrationRequestRepository) -> None:
    request = RegistrationRequest(
        uuid=UUID("530a57f4-8648-4f83-9ad5-c4d02ffd08ae"),
        user=mock_user(),
        valid_until=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
    )

    await reg_request_repo.add_request(request)
    await reg_request_repo.delete_request(request.uuid)

    the_request = await reg_request_repo.get_request(request.uuid)

    assert the_request is None
