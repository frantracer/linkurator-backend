from datetime import timedelta
from uuid import UUID

import pytest

from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_get_user_profile_handler() -> None:
    user_repository = InMemoryUserRepository()
    user = mock_user()
    await user_repository.add(user)

    handler = GetUserProfileHandler(user_repository)
    result = await handler.handle(user.uuid)

    assert result == user


@pytest.mark.asyncio()
async def test_get_user_profile_handler_user_not_found() -> None:
    user_repository = InMemoryUserRepository()
    handler = GetUserProfileHandler(user_repository)
    result = await handler.handle(UUID("1930a3ce-5f9c-4ee1-be67-6055c26cc4e2"))

    assert result is None


@pytest.mark.asyncio()
async def test_get_user_profile_handler_update_last_login_at() -> None:
    user_repository = InMemoryUserRepository()
    user = mock_user()
    await user_repository.add(user)

    handler = GetUserProfileHandler(user_repository)
    current_time = user.last_login_at + timedelta(minutes=61)
    result = await handler.handle(user_id=user.uuid, now_function=lambda: current_time)

    assert result is not None
    assert result.last_login_at == current_time


@pytest.mark.asyncio()
async def test_get_user_profile_handler_does_not_update_last_login_if_less_than_hour_passed() -> None:
    user_repository = InMemoryUserRepository()
    user = mock_user()
    await user_repository.add(user)

    handler = GetUserProfileHandler(user_repository)
    current_time = user.last_login_at + timedelta(minutes=59)
    result = await handler.handle(user_id=user.uuid, now_function=lambda: current_time)

    assert result is not None
    assert result.last_login_at == user.last_login_at
