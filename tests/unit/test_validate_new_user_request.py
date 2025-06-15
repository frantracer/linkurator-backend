from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import AnyUrl

from linkurator_core.application.auth.validate_new_user_request import ValidateNewUserRequest
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import InvalidRegistrationRequestError
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.infrastructure.in_memory.registration_request_repository import (
    InMemoryRegistrationRequestRepository,
)
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_validate_new_user_request() -> None:
    reg_request_repo = InMemoryRegistrationRequestRepository()
    user_repo = InMemoryUserRepository()
    event_bus = AsyncMock(spec=EventBusService)

    request = RegistrationRequest.new(
        user=mock_user(),
        seconds_to_expire=60,
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
    )
    await reg_request_repo.add_request(request)

    handler = ValidateNewUserRequest(
        registration_request_repository=reg_request_repo,
        user_repository=user_repo,
        event_bus=event_bus,
    )

    await handler.handle(request.uuid)

    assert await reg_request_repo.get_request(request.uuid) is None
    assert await user_repo.get(request.user.uuid) is not None
    assert len(event_bus.publish.call_args_list) == 1


@pytest.mark.asyncio()
async def test_expired_registration_request() -> None:
    reg_request_repo = InMemoryRegistrationRequestRepository()
    user_repo = InMemoryUserRepository()
    event_bus = AsyncMock(spec=EventBusService)

    request = RegistrationRequest.new(
        user=mock_user(),
        seconds_to_expire=-60,
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
    )
    await reg_request_repo.add_request(request)

    handler = ValidateNewUserRequest(
        registration_request_repository=reg_request_repo,
        user_repository=user_repo,
        event_bus=event_bus,
    )

    with pytest.raises(InvalidRegistrationRequestError):
        await handler.handle(request.uuid)

    assert await reg_request_repo.get_request(request.uuid) is None
    assert await user_repo.get(request.user.uuid) is None
    assert len(event_bus.publish.call_args_list) == 0


@pytest.mark.asyncio()
async def test_non_existent_registration_request() -> None:
    reg_request_repo = InMemoryRegistrationRequestRepository()
    user_repo = InMemoryUserRepository()
    event_bus = AsyncMock(spec=EventBusService)

    handler = ValidateNewUserRequest(
        registration_request_repository=reg_request_repo,
        user_repository=user_repo,
        event_bus=event_bus,
    )

    with pytest.raises(InvalidRegistrationRequestError):
        await handler.handle(request_uuid=UUID("40cf1c78-f881-496e-99f4-d258ae268974"))

    assert len(event_bus.publish.call_args_list) == 0
