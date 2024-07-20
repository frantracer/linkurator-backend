import uuid
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

import pytest

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio
async def test_get_subscriptions_handler_returns_results_paginated_and_filters_by_creation_date() -> None:
    sub1 = Subscription(
        uuid=uuid.UUID("6473ad5b-75ad-4384-a48d-924e026dd988"),
        name="Test1",
        url=utils.parse_url("https://url.com"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        scanned_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        last_published_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00")
    )
    sub2 = Subscription(
        uuid=uuid.UUID("79a636a4-6d4b-41e2-be73-4cff46110e28"),
        name="Test2",
        url=utils.parse_url("https://url.com"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        scanned_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        last_published_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00")
    )
    sub3 = Subscription(
        uuid=uuid.UUID("c497fecf-425c-4bb3-b597-5a3dc7ad2fe5"),
        name="Test3",
        url=utils.parse_url("https://url.com"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        scanned_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00"),
        last_published_at=datetime.fromisoformat("2020-01-01T00:00:00+00:00")
    )
    sub4 = Subscription(
        uuid=uuid.UUID("c66b1e29-79af-49d8-85f4-17d3b5d0bf76"),
        name="Test4",
        url=utils.parse_url("https://url.com"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        thumbnail=utils.parse_url("https://url.com/thumbnail.png"),
        created_at=datetime.fromisoformat("2050-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2050-01-01T00:00:00+00:00"),
        scanned_at=datetime.fromisoformat("2050-01-01T00:00:00+00:00"),
        last_published_at=datetime.fromisoformat("2050-01-01T00:00:00+00:00")
    )

    subscription_repo_mock = MagicMock()
    subscription_repo_mock.get_list.return_value = [sub4, sub3, sub2, sub1]
    user_repo_mock = AsyncMock(spec=UserRepository)
    user = User.new(
        uuid=uuid.UUID('84a6ad8f-e0e0-42a7-be27-ca79e65ec6b2'),
        first_name='John',
        last_name='Doe',
        email='jonh@email.com',
        locale='en',
        avatar_url=utils.parse_url("https://url.com/avatar.png"),
        google_refresh_token='token'
    )
    user_repo_mock.get.return_value = user
    handler = GetUserSubscriptionsHandler(subscription_repo_mock, user_repo_mock)

    the_subscriptions = await handler.handle(
        user_id=user.uuid,
        page_number=0,
        page_size=2,
        created_before=datetime.fromisoformat("2020-01-02T00:00:00+00:00")
    )

    assert the_subscriptions == [sub3, sub2]

    the_subscriptions = await handler.handle(
        user_id=user.uuid,
        page_number=1,
        page_size=2,
        created_before=datetime.fromisoformat("2020-01-02T00:00:00+00:00")
    )

    assert the_subscriptions == [sub1]

    the_subscriptions = await handler.handle(
        user_id=user.uuid,
        page_number=2,
        page_size=2,
        created_before=datetime.fromisoformat("2020-01-02T00:00:00+00:00")
    )

    assert the_subscriptions == []
