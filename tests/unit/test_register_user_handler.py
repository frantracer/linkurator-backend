import unittest
from unittest.mock import AsyncMock, MagicMock

from linkurator_core.application.auth.register_new_user_with_google import RegisterUserHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent, UserRegisteredEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.account_service import UserDetails, UserInfo
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class TestRegisterUserHandler(unittest.IsolatedAsyncioTestCase):

    async def test_register_an_user_with_valid_credentials(self) -> None:
        user_repo_mock = AsyncMock(spec=UserRepository)
        user_repo_mock.get_by_email.return_value = None

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = UserInfo(
            email="john@email.com",
            details=UserDetails(
                given_name="John",
                family_name="Doe",
                picture=utils.parse_url("https://example.com/john.jpg"),
                locale="en"
            ),
        )

        event_bus_mock = AsyncMock(spec=EventBusService)

        handler = RegisterUserHandler(user_repo_mock, account_service_mock, event_bus_mock)

        error = await handler.handle(access_token="mytoken", refresh_token="myrefreshtoken")

        self.assertIsNone(error)

        self.assertEqual(user_repo_mock.add.call_count, 1)
        created_user: User = user_repo_mock.add.call_args[0][0]
        self.assertEqual(created_user.first_name, "John")
        self.assertEqual(created_user.last_name, "Doe")
        self.assertEqual(created_user.email, "john@email.com")
        self.assertEqual(created_user.google_refresh_token, "myrefreshtoken")

        self.assertEqual(event_bus_mock.publish.call_count, 2)
        self.assertEqual(type(event_bus_mock.publish.call_args_list[0][0][0]), UserRegisteredEvent)
        self.assertEqual(type(event_bus_mock.publish.call_args_list[1][0][0]), UserSubscriptionsBecameOutdatedEvent)

    async def test_registering_existing_user_updates_the_user_data(self) -> None:
        user_repo_mock = AsyncMock(spec=UserRepository)
        user_repo_mock.get_by_email.return_value = mock_user()

        event_bus_mock = AsyncMock(spec=EventBusService)

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = UserInfo(
            email="john@email.com",
            details=UserDetails(
                given_name="John",
                family_name="Doe",
                picture=utils.parse_url("https://example.com/john.jpg"),
                locale="en"
            ),
        )

        handler = RegisterUserHandler(user_repo_mock, account_service_mock, event_bus_mock)

        error = await handler.handle(access_token="mytoken", refresh_token="myrefreshtoken")
        self.assertIsNone(error)

        self.assertEqual(user_repo_mock.update.call_count, 1)
        created_user: User = user_repo_mock.update.call_args[0][0]
        self.assertEqual(created_user.google_refresh_token, "myrefreshtoken")

        self.assertEqual(event_bus_mock.publish.call_count, 1)
        self.assertEqual(type(event_bus_mock.publish.call_args[0][0]), UserSubscriptionsBecameOutdatedEvent)

    async def test_registering_existing_user_with_refresh_token_do_not_update_current_token(self) -> None:
        user_repo_mock = AsyncMock(spec=UserRepository)
        user_repo_mock.get_by_email.return_value = mock_user(refresh_token="oldtoken")
        event_bus_mock = AsyncMock(spec=EventBusService)

        account_service_mock = MagicMock()
        account_service_mock.get_user_info.return_value = UserInfo(
            email="john@email.com",
            details=UserDetails(
                given_name="John",
                family_name="Doe",
                picture=utils.parse_url("https://example.com/john.jpg"),
                locale="en"
            ),
        )

        handler = RegisterUserHandler(user_repo_mock, account_service_mock, event_bus_mock)

        error = await handler.handle(access_token="mytoken", refresh_token=None)
        self.assertIsNone(error)

        self.assertEqual(user_repo_mock.update.call_count, 1)
        created_user: User = user_repo_mock.update.call_args[0][0]
        self.assertEqual(created_user.google_refresh_token, "oldtoken")

        self.assertEqual(event_bus_mock.publish.call_count, 1)
