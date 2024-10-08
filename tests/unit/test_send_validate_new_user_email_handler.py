from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import AnyUrl

from linkurator_core.application.auth.send_validate_new_user_email import SendValidateNewUserEmail
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.infrastructure.in_memory.registration_request_repository import \
    InMemoryRegistrationRequestRepository


@pytest.mark.asyncio
async def test_send_validate_new_user_email_handler_calls_email_sender_with_correct_parameters() -> None:
    email_sender = AsyncMock(spec=EmailSender)
    registration_request_repository = InMemoryRegistrationRequestRepository()
    user = mock_user()

    request = RegistrationRequest.new(
        user=user,
        seconds_to_expire=1,
        validation_base_url=AnyUrl("https://linkurator-test.com/validate"),
        uuid_generator=lambda: UUID("8fb9b6b4-7462-44d2-81a0-3ea48395bccb")
    )

    await registration_request_repository.add_request(request)

    handler = SendValidateNewUserEmail(email_sender, registration_request_repository)

    await handler.handle(request.uuid)

    assert email_sender.send_email.called
    assert email_sender.send_email.call_args.kwargs["user_email"] == user.email
    assert ("https://linkurator-test.com/validate/8fb9b6b4-7462-44d2-81a0-3ea48395bccb" in
            email_sender.send_email.call_args.kwargs["message_text"])


@pytest.mark.asyncio
async def test_send_validate_new_user_email_handler_with_not_existing_request_does_nothing() -> None:
    email_sender = AsyncMock(spec=EmailSender)
    registration_request_repository = InMemoryRegistrationRequestRepository()

    handler = SendValidateNewUserEmail(email_sender, registration_request_repository)

    await handler.handle(UUID("8fb9b6b4-7462-44d2-81a0-3ea48395bccb"))

    assert not email_sender.send_email.called
