import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from linkurator_core.application.auth.validate_session_token import ValidateTokenHandler
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


class TestValidateTokenHandler(unittest.IsolatedAsyncioTestCase):
    async def test_create_a_new_session(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = InMemoryUserRepository()
        dummy_user = mock_user()
        dummy_user.last_login_at = datetime.now(tz=timezone.utc) - timedelta(days=1)
        await user_repo_mock.add(dummy_user)

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = dummy_user

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        the_session = await handler.handle(access_token="mytoken")
        assert the_session is not None
        assert dummy_user.uuid == the_session.user_id

        updated_user = await user_repo_mock.get_by_email(dummy_user.email)
        assert updated_user is not None
        assert updated_user.last_login_at >= dummy_user.last_login_at

    async def test_an_existing_session_returns_a_session(self) -> None:
        session_repo_mock = MagicMock()
        user_id: uuid.UUID = uuid.UUID("15537505-3cc9-441a-9eb7-36045042fb4d")
        dummy_session = Session("mytoken", user_id, datetime.now(tz=timezone.utc) + timedelta(days=1))
        session_repo_mock.get.return_value = dummy_session

        user_repo_mock = MagicMock()
        dummy_user = mock_user(uuid=user_id)
        user_repo_mock.get.return_value = dummy_user

        account_service_mock = MagicMock()

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        the_session = await handler.handle(access_token="mytoken")
        assert dummy_session == the_session

    async def test_a_invalid_session_returns_none(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        user_repo_mock.get_by_email.return_value = None

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = None

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        the_session = await handler.handle(access_token="mytoken")
        assert the_session is None

    async def test_an_expired_session_returns_none(self) -> None:
        session_repo_mock = MagicMock()

        session_repo_mock.get.return_value = Session(
            token="mytoken",
            user_id=uuid.uuid4(),
            expires_at=datetime.now(tz=timezone.utc) - timedelta(days=1))

        user_repo_mock = MagicMock()

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = None

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        the_session = await handler.handle(access_token="mytoken")
        assert the_session is None
