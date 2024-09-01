from unittest.mock import MagicMock

import pytest

from linkurator_core.application.users.delete_user_handler import DeleteUserHandler
from linkurator_core.domain.common.exceptions import FailToRevokeCredentialsError
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.account_service import AccountService
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_delete_user_handler() -> None:
    user_repository = InMemoryUserRepository()
    session_repository = MagicMock(spec=SessionRepository)
    session_repository.delete.return_value = None
    account_service = MagicMock(spec=AccountService)
    account_service.revoke_credentials.return_value = None

    user = mock_user()
    await user_repository.add(user)

    session = Session.new(user_id=user.uuid, seconds_to_expire=3600)

    handler = DeleteUserHandler(user_repository, session_repository, account_service)

    await handler.handle(session)

    assert await user_repository.get(user.uuid) is None
    assert len(account_service.revoke_credentials.call_args_list) == 1
    assert len(session_repository.delete.call_args_list) == 1


@pytest.mark.asyncio
async def test_delete_user_handler_user_not_found() -> None:
    user_repository = InMemoryUserRepository()
    session_repository = MagicMock(spec=SessionRepository)
    account_service = MagicMock(spec=AccountService)

    user = mock_user()
    session = Session.new(user_id=user.uuid, seconds_to_expire=3600)

    handler = DeleteUserHandler(user_repository, session_repository, account_service)

    await handler.handle(session)

    assert len(account_service.revoke_credentials.call_args_list) == 0
    assert len(session_repository.delete.call_args_list) == 0


@pytest.mark.asyncio
async def test_delete_user_handler_fail_to_revoke_credentials() -> None:
    user_repository = InMemoryUserRepository()
    session_repository = MagicMock(spec=SessionRepository)
    account_service = MagicMock(spec=AccountService)
    account_service.revoke_credentials.side_effect = FailToRevokeCredentialsError

    user = mock_user()
    await user_repository.add(user)

    session = Session.new(user_id=user.uuid, seconds_to_expire=3600)

    handler = DeleteUserHandler(user_repository, session_repository, account_service)

    await handler.handle(session)

    assert await user_repository.get(user.uuid) is None
    assert len(account_service.revoke_credentials.call_args_list) == 1
    assert len(session_repository.delete.call_args_list) == 1
