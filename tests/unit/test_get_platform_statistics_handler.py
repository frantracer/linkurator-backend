from datetime import datetime, timedelta, timezone

import pytest

from linkurator_core.application.statistics.get_platform_statistics import GetPlatformStatisticsHandler
from linkurator_core.domain.common.mock_factory import mock_item, mock_sub, mock_user
from linkurator_core.domain.items.item import ItemProvider
from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_get_platform_statistics_handler() -> None:
    # Given
    now = datetime.now(timezone.utc)
    user_repository = InMemoryUserRepository()
    user1 = mock_user()
    user1.last_login_at = now - timedelta(hours=23)
    user2 = mock_user()
    user2.last_login_at = now - timedelta(hours=24)
    await user_repository.add(user1)
    await user_repository.add(user2)

    subscription_repository = InMemorySubscriptionRepository()
    subscription1 = mock_sub(provider=SubscriptionProvider.YOUTUBE)
    subscription2 = mock_sub(provider=SubscriptionProvider.SPOTIFY)
    subscription3 = mock_sub(provider=SubscriptionProvider.YOUTUBE)
    await subscription_repository.add(subscription1)
    await subscription_repository.add(subscription2)
    await subscription_repository.add(subscription3)

    item_repository = InMemoryItemRepository()
    item1 = mock_item(provider=ItemProvider.YOUTUBE)
    item2 = mock_item(provider=ItemProvider.SPOTIFY)
    item3 = mock_item(provider=ItemProvider.YOUTUBE)
    item4 = mock_item(provider=ItemProvider.SPOTIFY)
    item5 = mock_item(provider=ItemProvider.YOUTUBE)
    await item_repository.upsert_items([item1, item2, item3, item4, item5])

    handler = GetPlatformStatisticsHandler(user_repository, subscription_repository, item_repository)

    # When
    statistics = await handler.handle()

    # Then
    assert statistics.users.registered == 2
    assert statistics.users.active == 1
    assert statistics.subscriptions.total == 3
    assert statistics.subscriptions.youtube == 2
    assert statistics.subscriptions.spotify == 1
    assert statistics.items.total == 5
    assert statistics.items.youtube == 3
    assert statistics.items.spotify == 2
