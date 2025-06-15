from unittest.mock import AsyncMock

import pytest
from pydantic import AnyUrl

from linkurator_core.application.auth.register_new_user_with_email import RegisterNewUserWithEmail, RegistrationError
from linkurator_core.domain.common.event import UserRegisterRequestSentEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.user import Username
from linkurator_core.infrastructure.in_memory.registration_request_repository import (
    InMemoryRegistrationRequestRepository,
)
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_register_new_user_with_email() -> None:
    user_repo = InMemoryUserRepository()
    registration_request_repository = InMemoryRegistrationRequestRepository()
    event_bus = AsyncMock(spec=EventBusService)

    handler = RegisterNewUserWithEmail(user_repo, registration_request_repository, event_bus)

    errors = await handler.handle(
        email="test@email.com",
        password="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        first_name="John",
        last_name="Doe",
        username=Username("johndoe"),
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
    )

    assert len(errors) == 0
    new_user = await user_repo.get_by_email("test@email.com")
    assert new_user is None

    assert event_bus.publish.call_count == 1
    published_event = event_bus.publish.call_args_list[0][1]["event"]

    assert isinstance(published_event, UserRegisterRequestSentEvent)
    assert await registration_request_repository.get_request(published_event.request_uuid) is not None


@pytest.mark.asyncio()
async def test_register_new_user_with_email_email_already_registered() -> None:
    user_repo = InMemoryUserRepository()
    registration_request_repository = InMemoryRegistrationRequestRepository()
    event_bus = AsyncMock(spec=EventBusService)

    handler = RegisterNewUserWithEmail(user_repo, registration_request_repository, event_bus)

    user = mock_user(email="test@email.com")
    await user_repo.add(user)

    errors = await handler.handle(
        email="test@email.com",
        password="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        first_name="John",
        last_name="Doe",
        username=Username("johndoe"),
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
    )

    assert len(errors) == 1
    assert errors[0] == RegistrationError.EMAIL_ALREADY_REGISTERED

    assert event_bus.publish.call_count == 0


@pytest.mark.asyncio()
async def test_register_new_user_with_all_errors() -> None:
    user_repo = InMemoryUserRepository()
    registration_request_repository = InMemoryRegistrationRequestRepository()
    event_bus = AsyncMock(spec=EventBusService)

    handler = RegisterNewUserWithEmail(user_repo, registration_request_repository, event_bus)

    user = mock_user(email="test@email.com", username=Username("johndoe"))
    await user_repo.add(user)

    errors = await handler.handle(
        email="test@email.com",
        password="2",
        first_name="John",
        last_name="Doe",
        username=Username("johndoe"),
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
    )

    assert len(errors) == 3
    assert RegistrationError.EMAIL_ALREADY_REGISTERED in errors
    assert RegistrationError.USERNAME_ALREADY_REGISTERED in errors
    assert RegistrationError.PASSWORD_MUST_BE_HEX_WITH_64_DIGITS in errors

    assert event_bus.publish.call_count == 0
