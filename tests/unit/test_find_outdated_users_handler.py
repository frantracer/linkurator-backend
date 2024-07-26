from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.users.find_outdated_users_handler import FindOutdatedUsersHandler
from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio
async def test_handler_sends_two_events_if_there_are_two_outdated_users() -> None:
    user_repo_mock = AsyncMock(spec=UserRepository)
    user1 = mock_user()
    user2 = mock_user()
    user_repo_mock.find_latest_scan_before.return_value = [user1, user2]

    event_bus_mock = AsyncMock()
    handler = FindOutdatedUsersHandler(user_repo_mock, event_bus_mock)

    await handler.handle()

    assert event_bus_mock.publish.call_count == 2
    arg1 = event_bus_mock.publish.call_args_list[0][0][0]
    assert isinstance(arg1, UserSubscriptionsBecameOutdatedEvent)
    assert arg1.user_id == user1.uuid
    arg2 = event_bus_mock.publish.call_args_list[1][0][0]
    assert isinstance(arg2, UserSubscriptionsBecameOutdatedEvent)
    assert arg2.user_id == user2.uuid
