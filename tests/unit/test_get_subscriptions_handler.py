import datetime
from unittest.mock import MagicMock
import uuid

from linkurator_core.common import utils
from linkurator_core.domain.subscription import Subscription
from linkurator_core.domain.user import User
from linkurator_core.application.get_user_subscriptions_handler import GetUserSubscriptionsHandler


def test_get_subscriptions_handler_returns_results_paginated_and_filters_by_creation_date():
    sub1 = Subscription(
        uuid=uuid.UUID("6473ad5b-75ad-4384-a48d-924e026dd988"),
        name="Test1",
        url=utils.parse_url("https://url.com"),
        provider='test',
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        updated_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        scanned_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00")
    )
    sub2 = Subscription(
        uuid=uuid.UUID("79a636a4-6d4b-41e2-be73-4cff46110e28"),
        name="Test2",
        url=utils.parse_url("https://url.com"),
        provider='test',
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        updated_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        scanned_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00")
    )
    sub3 = Subscription(
        uuid=uuid.UUID("c497fecf-425c-4bb3-b597-5a3dc7ad2fe5"),
        name="Test3",
        url=utils.parse_url("https://url.com"),
        provider='test',
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        updated_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        scanned_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00")
    )
    sub4 = Subscription(
        uuid=uuid.UUID("c66b1e29-79af-49d8-85f4-17d3b5d0bf76"),
        name="Test4",
        url=utils.parse_url("https://url.com"),
        provider='test',
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.datetime.fromisoformat("2050-01-01T00:00:00"),
        updated_at=datetime.datetime.fromisoformat("2050-01-01T00:00:00"),
        scanned_at=datetime.datetime.fromisoformat("2050-01-01T00:00:00")
    )

    subscription_repo_mock = MagicMock()
    subscription_repo_mock.get_list.return_value = [sub4, sub3, sub2, sub1]
    user_repo_mock = MagicMock()
    user = User.new(
        uuid=uuid.UUID('84a6ad8f-e0e0-42a7-be27-ca79e65ec6b2'),
        first_name='John',
        last_name='Doe',
        email='jonh@email.com',
        google_refresh_token='token'
    )
    user_repo_mock.get.return_value = user
    handler = GetUserSubscriptionsHandler(subscription_repo_mock, user_repo_mock)

    the_subscriptions, total_subscriptions = handler.handle(
        user_id=user.uuid,
        page_number=0,
        page_size=2,
        created_before=datetime.datetime.fromisoformat('2020-01-02T00:00:00.000000')
    )

    assert the_subscriptions == [sub3, sub2]
    assert total_subscriptions == 3

    the_subscriptions, total_subscriptions = handler.handle(
        user_id=user.uuid,
        page_number=1,
        page_size=2,
        created_before=datetime.datetime.fromisoformat('2020-01-02T00:00:00.000000')
    )

    assert the_subscriptions == [sub1]
    assert total_subscriptions == 3

    the_subscriptions, total_subscriptions = handler.handle(
        user_id=user.uuid,
        page_number=2,
        page_size=2,
        created_before=datetime.datetime.fromisoformat('2020-01-02T00:00:00.000000')
    )

    assert the_subscriptions == []
    assert total_subscriptions == 3
