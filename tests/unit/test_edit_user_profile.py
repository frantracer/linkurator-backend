import pytest

from linkurator_core.application.users.edit_user_profile import EditUserProfile, NewProfileAttributes
from linkurator_core.domain.common.exceptions import UsernameAlreadyInUseError
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.common.utils import datetime_now
from linkurator_core.domain.users.user import Username
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_edit_user_first_name_and_last_name() -> None:
    user_repo = InMemoryUserRepository()
    user = mock_user()
    await user_repo.add(user)

    now = datetime_now()
    handler = EditUserProfile(user_repo, now_function=lambda: now)

    new_first_name = "New First Name"
    new_last_name = "New Last Name"
    await handler.handle(user.uuid, NewProfileAttributes(first_name=new_first_name, last_name=new_last_name))

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.first_name == new_first_name
    assert updated_user.last_name == new_last_name
    assert updated_user.updated_at == now


@pytest.mark.asyncio
async def test_edit_username() -> None:
    user_repo = InMemoryUserRepository()
    user = mock_user()
    await user_repo.add(user)

    now = datetime_now()
    handler = EditUserProfile(user_repo, now_function=lambda: now)

    new_username = Username("new_username")
    await handler.handle(user.uuid, NewProfileAttributes(username=new_username))

    updated_user = await user_repo.get(user.uuid)
    assert updated_user is not None
    assert updated_user.username == new_username
    assert updated_user.updated_at == now


@pytest.mark.asyncio
async def test_edit_username_with_existing_one_returns_error() -> None:
    user_repo = InMemoryUserRepository()
    user = mock_user()
    await user_repo.add(user)

    existing_user = mock_user()
    await user_repo.add(existing_user)

    handler = EditUserProfile(user_repo)

    with pytest.raises(UsernameAlreadyInUseError):
        await handler.handle(user.uuid, NewProfileAttributes(username=existing_user.username))
