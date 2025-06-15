import datetime
from unittest.mock import MagicMock

import pytest

from linkurator_core.application.subscriptions.find_outdated_subscriptions_handler import (
    FindOutdatedSubscriptionsHandler,
)
from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio()
async def test_handler_sends_two_events_if_there_are_two_outdated_subscriptions() -> None:
    sub_repo_mock = InMemorySubscriptionRepository()
    sub1 = mock_sub()
    sub1.updated_at = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=25)
    sub2 = mock_sub()
    sub2.updated_at = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=25)
    sub3 = mock_sub()
    sub3.updated_at = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=23)
    await sub_repo_mock.add(sub1)
    await sub_repo_mock.add(sub2)
    await sub_repo_mock.add(sub3)

    event_bus_mock = MagicMock(spec=EventBusService)
    handler = FindOutdatedSubscriptionsHandler(
        subscription_repository=sub_repo_mock,
        event_bus=event_bus_mock)
    await handler.handle()

    assert event_bus_mock.publish.call_count == 2
    arg1 = event_bus_mock.publish.call_args_list[0][0][0]
    arg2 = event_bus_mock.publish.call_args_list[1][0][0]

    assert isinstance(arg1, SubscriptionBecameOutdatedEvent)
    assert isinstance(arg2, SubscriptionBecameOutdatedEvent)

    assert {sub1.uuid, sub2.uuid}.issubset({arg1.subscription_id, arg2.subscription_id})
