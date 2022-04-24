from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock
import uuid

from linkurator_core.application.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.session import Session
from linkurator_core.domain.user import User


class TestValidateTokenHandler(unittest.TestCase):
    def test_an_existing_session_returns_a_session(self):
        session_repo_mock = MagicMock()
        user_id: uuid.UUID = uuid.UUID("15537505-3cc9-441a-9eb7-36045042fb4d")
        dummy_session = Session("mytoken", user_id, datetime.now() + timedelta(days=1))
        session_repo_mock.get.return_value = dummy_session

        user_repo_mock = MagicMock()
        dummy_user = User(user_id, "Jonh", "john@example.com", datetime.now(), datetime.now(), "myrefreshtoken")
        user_repo_mock.get.return_value = dummy_user

        account_service_mock = MagicMock()

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        the_session = handler.handle(access_token="mytoken")
        self.assertEqual(dummy_session, the_session)

    def test_a_invalid_session_returns_none(self):
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        user_repo_mock.get_by_email.return_value = None

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = None

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        user = handler.handle(access_token="mytoken")
        self.assertIsNone(user)

    def test_an_expired_session_returns_none(self):
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = Session("mytoken", uuid.uuid4(), datetime.now() - timedelta(days=1))

        user_repo_mock = MagicMock()

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = None

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock)

        user = handler.handle(access_token="mytoken")
        self.assertIsNone(user)
