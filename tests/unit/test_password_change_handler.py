from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.auth.request_password_change import RequestPasswordChange
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.notifications.email_sender import EmailSender
from linkurator_core.infrastructure.in_memory.password_change_request_repository import \
    InMemoryPasswordChangeRequestRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_request_password_change_handler() -> None:
    user_repo = InMemoryUserRepository()
    password_change_request_repository = InMemoryPasswordChangeRequestRepository()
    email_sender = AsyncMock(spec=EmailSender)
    email_sender.send_email.return_value = True
    base_url = "https://linkurator.com/change-password"

    user = mock_user()
    await user_repo.add(user)
    request_uuid = UUID("adfa8e71-bbbb-40ae-9fc9-f7d6e2dfc368")

    handler = RequestPasswordChange(
        user_repository=user_repo,
        password_change_request_repository=password_change_request_repository,
        email_sender=email_sender,
        base_url=base_url,
        uuid_generator=lambda: request_uuid
    )

    await handler.handle(email=user.email)

    assert len(email_sender.send_email.call_args_list) == 1
    assert f"{base_url}/{str(request_uuid)}" in email_sender.send_email.call_args_list[0][0][2]
    assert await password_change_request_repository.get_request(request_uuid) is not None
