import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock

from linkurator_core.application.users.register_user_handler import RegisterUserHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.users.account_service import UserDetails, UserInfo
from linkurator_core.domain.users.user import User


class TestRegisterUserHandler(unittest.IsolatedAsyncioTestCase):

    async def test_register_an_user_with_valid_credentials(self) -> None:
        user_repo_mock = MagicMock()
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

        self.assertEqual(event_bus_mock.publish.call_count, 1)
        self.assertEqual(type(event_bus_mock.publish.call_args[0][0]), UserSubscriptionsBecameOutdatedEvent)

    async def test_registering_existing_user_updates_the_user_data(self) -> None:
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

        self.assertEqual(event_bus_mock.publish.call_count, 0)
