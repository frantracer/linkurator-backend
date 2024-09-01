from datetime import datetime, timezone

import pytest

from linkurator_core.application.auth.change_password_from_request import ChangePasswordFromRequest
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.infrastructure.in_memory.password_change_request_repository import \
    InMemoryPasswordChangeRequestRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_change_password_from_request() -> None:
    user_repo = InMemoryUserRepository()
    password_change_request_repository = InMemoryPasswordChangeRequestRepository()

    user = mock_user()
    user.set_password("2222222222222222222222222222222222222222222222222222222222222222")
    await user_repo.add(user)

    request = PasswordChangeRequest.new(user_id=user.uuid, seconds_to_expire=600)
    await password_change_request_repository.add_request(request)

    handler = ChangePasswordFromRequest(
        request_repository=password_change_request_repository,
        user_repository=user_repo)

    new_password = "1111111111111111111111111111111111111111111111111111111111111111"
    result = await handler.handle(request_id=request.uuid, new_password=new_password)

    assert result is True
    assert await password_change_request_repository.get_request(request.uuid) is None
    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.validate_password(new_password) is True


@pytest.mark.asyncio
async def test_change_password_from_expired_request() -> None:
    user_repo = InMemoryUserRepository()
    password_change_request_repository = InMemoryPasswordChangeRequestRepository()

    user = mock_user()
    initial_password = "2222222222222222222222222222222222222222222222222222222222222222"
    user.set_password(initial_password)
    await user_repo.add(user)

    request = PasswordChangeRequest.new(user_id=user.uuid, seconds_to_expire=60,
                                        now_function=lambda: datetime.fromtimestamp(0, tz=timezone.utc))

    await password_change_request_repository.add_request(request)

    handler = ChangePasswordFromRequest(
        request_repository=password_change_request_repository,
        user_repository=user_repo)

    new_password = "1111111111111111111111111111111111111111111111111111111111111111"
    result = await handler.handle(request_id=request.uuid, new_password=new_password)

    assert result is False
    assert await password_change_request_repository.get_request(request.uuid) is None
    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.validate_password(initial_password) is True


@pytest.mark.asyncio
async def test_change_password_from_non_existing_request() -> None:
    user_repo = InMemoryUserRepository()
    password_change_request_repository = InMemoryPasswordChangeRequestRepository()

    user = mock_user()
    await user_repo.add(user)

    handler = ChangePasswordFromRequest(
        request_repository=password_change_request_repository,
        user_repository=user_repo)

    new_password = "1111111111111111111111111111111111111111111111111111111111111111"
    result = await handler.handle(request_id=user.uuid, new_password=new_password)

    assert result is False
    assert await password_change_request_repository.get_request(user.uuid) is None
