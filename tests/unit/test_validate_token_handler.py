import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from linkurator_core.application.users.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.user import User


class TestValidateTokenHandler(unittest.IsolatedAsyncioTestCase):
    async def test_an_existing_session_returns_a_session(self) -> None:
        session_repo_mock = MagicMock()
        user_id: uuid.UUID = uuid.UUID("15537505-3cc9-441a-9eb7-36045042fb4d")
        dummy_session = Session("mytoken", user_id, datetime.now(tz=timezone.utc) + timedelta(days=1))
        session_repo_mock.get.return_value = dummy_session

        user_repo_mock = MagicMock()
        dummy_user = User.new(uuid=user_id,
                              first_name="John",
                              last_name="Doe",
                              email="john@example.com",
                              locale="en",
                              avatar_url=utils.parse_url("https://example.com/john.jpg"),
                              google_refresh_token="myrefreshtoken")
        user_repo_mock.get.return_value = dummy_user

        account_service_mock = MagicMock()

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        the_session = await handler.handle(access_token="mytoken")
        self.assertEqual(dummy_session, the_session)

    async def test_a_invalid_session_returns_none(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        user_repo_mock.get_by_email.return_value = None

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = None

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        the_session = await handler.handle(access_token="mytoken")
        self.assertIsNone(the_session)

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
        self.assertIsNone(the_session)
