import uuid
from unittest.mock import MagicMock

from linkurator_core.application.subscriptions.find_outdated_subscriptions_handler import \
    FindOutdatedSubscriptionsHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.event import SubscriptionBecameOutdatedEvent
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider


def test_handler_sends_two_events_if_there_are_two_outdated_subscriptions():
    sub_repo_mock = MagicMock()
    sub1 = Subscription.new(
        uuid=uuid.uuid4(),
        provider=SubscriptionProvider.YOUTUBE,
        name='Test',
        url=utils.parse_url('https://www.youtube.com/channel/test1'),
        thumbnail=utils.parse_url('https://www.youtube.com/channel/test/thumbnail1'),
        external_data={},
    )
    sub2 = Subscription.new(
        uuid=uuid.uuid4(),
        provider=SubscriptionProvider.YOUTUBE,
        name='Test',
        url=utils.parse_url('https://www.youtube.com/channel/test2'),
        thumbnail=utils.parse_url('https://www.youtube.com/channel/test/thumbnail2'),
        external_data={},
    )
    sub_repo_mock.find_latest_scan_before.return_value = [sub1, sub2]

    event_bus_mock = MagicMock()
    handler = FindOutdatedSubscriptionsHandler(sub_repo_mock, event_bus_mock)

    handler.handle()

    assert event_bus_mock.publish.call_count == 2
    arg1 = event_bus_mock.publish.call_args_list[0][0][0]
    arg2 = event_bus_mock.publish.call_args_list[1][0][0]

    assert isinstance(arg1, SubscriptionBecameOutdatedEvent)
    assert isinstance(arg2, SubscriptionBecameOutdatedEvent)

    assert {sub1.uuid, sub2.uuid}.issubset({arg1.subscription_id, arg2.subscription_id})
