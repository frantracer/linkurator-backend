from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import AnyUrl

from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.domain.users.password_change_request_repository import PasswordChangeRequestRepository
from linkurator_core.infrastructure.in_memory.password_change_request_repository import (
    InMemoryPasswordChangeRequestRepository,
)
from linkurator_core.infrastructure.mongodb.password_change_request_repository import (
    MongoDBPasswordChangeRequestRepository,
)
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="pass_change_request_repo", scope="session", params=["mongodb", "in_memory"])
def fixture_password_change_repository(db_name: str, request: Any) -> PasswordChangeRequestRepository:
    if request.param == "in_memory":
        return InMemoryPasswordChangeRequestRepository()
    return MongoDBPasswordChangeRequestRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio()
async def test_exception_is_raised_if_registration_request_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBPasswordChangeRequestRepository(
            IPv4Address("127.0.0.1"), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio()
async def test_add_request(pass_change_request_repo: PasswordChangeRequestRepository) -> None:
    request = PasswordChangeRequest(
        uuid=UUID("fae509b1-4b54-4c9a-84bb-b8f05ae48bb2"),
        user_id=UUID("e76c71f3-1717-48d5-9f7c-d0cc4b3a0a6a"),
        valid_until=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        validation_base_url=AnyUrl("http://localhost"),
    )

    await pass_change_request_repo.add_request(request)
    the_request = await pass_change_request_repo.get_request(request.uuid)

    assert the_request is not None
    assert the_request.uuid == request.uuid


@pytest.mark.asyncio()
async def test_get_request_that_does_not_exist(pass_change_request_repo: PasswordChangeRequestRepository) -> None:
    the_request = await pass_change_request_repo.get_request(UUID("28a817e3-11ec-4830-9136-796e69b3d2fa"))

    assert the_request is None


@pytest.mark.asyncio()
async def test_delete_request(pass_change_request_repo: PasswordChangeRequestRepository) -> None:
    request = PasswordChangeRequest(
        uuid=UUID("d3b97d65-3f5b-4f93-8932-bfa162bf1480"),
        user_id=UUID("71d701ec-dd9e-4018-ad13-bc14b261e46f"),
        valid_until=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        validation_base_url=AnyUrl("http://localhost"),
    )

    await pass_change_request_repo.add_request(request)
    await pass_change_request_repo.delete_request(request.uuid)

    the_request = await pass_change_request_repo.get_request(request.uuid)

    assert the_request is None
