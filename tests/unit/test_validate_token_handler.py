import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock

from linkurator_core.application.users.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.users.account_service import UserInfo
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
        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock, event_bus_mock)

        the_session = await handler.handle(access_token="mytoken", refresh_token=None)
        self.assertEqual(dummy_session, the_session)
        self.assertEqual(event_bus_mock.publish.call_count, 0)

    async def test_a_non_existing_session_updates_user_information(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        dummy_user = User(uuid=uuid.uuid4(),
                          first_name="John",
                          last_name="Doe",
                          email="john@example.com",
                          locale="en",
                          avatar_url=utils.parse_url("https://example.com/john.jpg"),
                          google_refresh_token="oldtoken",
                          subscription_uuids=[],
                          created_at=datetime.fromtimestamp(0, tz=timezone.utc),
                          updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
                          last_login_at=datetime.fromtimestamp(0, tz=timezone.utc),
                          scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
                          is_admin=False)
        user_repo_mock.get_by_email.return_value = dummy_user

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = UserInfo(
            given_name="New name",
            family_name="New last name",
            email="john@example.com",
            picture=utils.parse_url("https://example.com/new.jpg"),
            locale="es"
        )

        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock, event_bus_mock)

        the_session = await handler.handle(access_token="mytoken", refresh_token="myrefreshtoken")
        self.assertIsNotNone(the_session)
        self.assertEqual(user_repo_mock.update.call_count, 1)
        input_user: User = user_repo_mock.update.call_args[0][0]
        self.assertEqual(input_user.first_name, "New name")
        self.assertEqual(input_user.last_name, "New last name")
        self.assertEqual(input_user.email, "john@example.com")
        self.assertEqual(input_user.avatar_url, utils.parse_url("https://example.com/new.jpg"))
        self.assertEqual(input_user.locale, "es")
        self.assertEqual(input_user.google_refresh_token, "myrefreshtoken")
        self.assertGreater(input_user.updated_at, datetime.fromtimestamp(0, tz=timezone.utc))
        self.assertGreater(input_user.last_login_at, datetime.fromtimestamp(0, tz=timezone.utc))

        self.assertEqual(event_bus_mock.publish.call_count, 0)

    async def test_a_invalid_session_returns_none(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        user_repo_mock.get_by_email.return_value = None

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = None

        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock, event_bus_mock)

        the_session = await handler.handle(access_token="mytoken", refresh_token=None)
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

        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock, event_bus_mock)

        the_session = await handler.handle(access_token="mytoken", refresh_token=None)
        self.assertIsNone(the_session)

    async def test_valid_credentials_registers_a_user(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        user_repo_mock.get_by_email.return_value = None

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = UserInfo(
            given_name="John",
            family_name="Doe",
            email="john@email.com",
            picture=utils.parse_url("https://example.com/john.jpg"),
            locale="en"
        )

        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock, event_bus_mock)

        the_session = await handler.handle(access_token="mytoken", refresh_token="myrefreshtoken")
        self.assertIsNotNone(the_session)

        self.assertEqual(user_repo_mock.add.call_count, 1)
        created_user: User = user_repo_mock.add.call_args[0][0]
        self.assertEqual(created_user.first_name, "John")
        self.assertEqual(created_user.last_name, "Doe")
        self.assertEqual(created_user.email, "john@email.com")
        self.assertEqual(created_user.google_refresh_token, "myrefreshtoken")

        self.assertEqual(event_bus_mock.publish.call_count, 1)
        self.assertEqual(type(event_bus_mock.publish.call_args[0][0]), UserSubscriptionsBecameOutdatedEvent)

    async def test_non_null_refresh_token_updates_user_refresh_token(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        user_repo_mock.get_by_email.return_value = User.new(
            uuid=uuid.uuid4(),
            first_name="John",
            last_name="Doe",
            email="john@email.com",
            locale="en",
            avatar_url=utils.parse_url("https://example.com/john.jpg"),
            google_refresh_token="oldtoken"
        )

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = UserInfo(
            given_name="John",
            family_name="Doe",
            email="john@email.com",
            picture=utils.parse_url("https://example.com/john.jpg"),
            locale="en"
        )

        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock, event_bus_mock)

        the_session = await handler.handle(access_token="mytoken", refresh_token="myrefreshtoken")
        self.assertIsNotNone(the_session)

        self.assertEqual(user_repo_mock.update.call_count, 1)
        created_user: User = user_repo_mock.update.call_args[0][0]
        self.assertEqual(created_user.google_refresh_token, "myrefreshtoken")

    async def test_null_refresh_token_does_not_update_user_refresh_token(self) -> None:
        session_repo_mock = MagicMock()
        session_repo_mock.get.return_value = None

        user_repo_mock = MagicMock()
        user_repo_mock.get_by_email.return_value = User.new(
            uuid=uuid.uuid4(),
            first_name="John",
            last_name="Doe",
            email="jonh@email.com",
            locale="en",
            avatar_url=utils.parse_url("https://example.com/john.jpg"),
            google_refresh_token="oldtoken"
        )

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = UserInfo(
            given_name="John",
            family_name="Doe",
            email="jonh@email.com",
            picture=utils.parse_url("https://example.com/john.jpg"),
            locale="en"
        )

        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = ValidateTokenHandler(user_repo_mock, session_repo_mock, account_service_mock, event_bus_mock)

        the_session = await handler.handle(access_token="mytoken", refresh_token=None)
        self.assertIsNotNone(the_session)

        self.assertEqual(user_repo_mock.delete.call_count, 0)
        self.assertEqual(user_repo_mock.add.call_count, 0)
