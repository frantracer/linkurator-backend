import uuid
from unittest.mock import MagicMock

import pytest

from linkurator_core.application.users.find_outdated_users_handler import FindOutdatedUsersHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.domain.users.user import User


@pytest.mark.asyncio
async def test_handler_sends_two_events_if_there_are_two_outdated_users() -> None:
    user_repo_mock = MagicMock()
    user1 = User.new(uuid=uuid.UUID("844f3bfb-ddab-4280-a3e6-fabc53a2984b"),
                     first_name='user1',
                     last_name="name1",
                     email='mock1@email.com',
                     locale='en',
                     avatar_url=utils.parse_url('https://example.com/avatar.png'),
                     google_refresh_token="token")
    user2 = User.new(uuid=uuid.UUID("844f3bfb-ddab-4280-a3e6-fabc53a2984b"),
                     first_name='user2',
                     last_name="name2",
                     email='mock2@email.com',
                     locale='en',
                     avatar_url=utils.parse_url('https://example.com/avatar.png'),
                     google_refresh_token="token")
    user_repo_mock.find_latest_scan_before.return_value = [user1, user2]

    event_bus_mock = MagicMock()
    handler = FindOutdatedUsersHandler(user_repo_mock, event_bus_mock)

    await handler.handle()

    assert event_bus_mock.publish.call_count == 2
    arg1 = event_bus_mock.publish.call_args_list[0][0][0]
    assert isinstance(arg1, UserSubscriptionsBecameOutdatedEvent)
    assert arg1.user_id == user1.uuid
    arg2 = event_bus_mock.publish.call_args_list[1][0][0]
    assert isinstance(arg2, UserSubscriptionsBecameOutdatedEvent)
    assert arg2.user_id == user2.uuid
