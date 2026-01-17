from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from linkurator_core.domain.common.exceptions import InvalidRssFeedError
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.item import ItemProvider
from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.rss_data_repository import InMemoryRssDataRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.rss.rss_feed_client import RssFeedClient, RssFeedInfo, RssFeedItem
from linkurator_core.infrastructure.rss.rss_service import RssSubscriptionService


@pytest.mark.asyncio()
async def test_get_subscriptions_returns_empty_list() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()
    rss_client_mock = AsyncMock(spec=RssFeedClient)

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    subscriptions = await service.get_subscriptions(user_id=uuid4(), access_token="token")
    assert subscriptions == []


@pytest.mark.asyncio()
async def test_get_subscription_updates_feed_info() -> None:
    # Create existing subscription
    sub = mock_sub()
    sub.provider = SubscriptionProvider.RSS
    sub.external_data = {
        "feed_url": "https://example.com/feed.xml",
        "language": "en",
        "link": "https://example.com",
    }

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    # Mock RSS client
    rss_client_mock = AsyncMock(spec=RssFeedClient)
    rss_client_mock.get_feed_info.return_value = RssFeedInfo(
        title="Updated Feed Title",
        link="https://example.com",
        description="Updated description",
        thumbnail="https://example.com/image.png",
        language="en",
    )

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    updated_sub = await service.get_subscription(sub.uuid)

    assert updated_sub is not None
    assert updated_sub.name == "Updated Feed Title"
    assert updated_sub.description == "Updated description"
    assert str(updated_sub.thumbnail) == "https://example.com/image.png"
    assert str(updated_sub.url) == "https://example.com/feed.xml"


@pytest.mark.asyncio()
async def test_get_subscription_returns_none_for_non_rss() -> None:
    # Create YouTube subscription
    sub = mock_sub()
    sub.provider = SubscriptionProvider.YOUTUBE

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    result = await service.get_subscription(sub.uuid)
    assert result is None


@pytest.mark.asyncio()
async def test_get_subscription_returns_none_on_error() -> None:
    sub = mock_sub()
    sub.provider = SubscriptionProvider.RSS
    sub.external_data = {"feed_url": "https://example.com/feed.xml"}

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)
    rss_client_mock.get_feed_info.side_effect = InvalidRssFeedError("Feed error")

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    result = await service.get_subscription(sub.uuid)
    assert result is None


@pytest.mark.asyncio()
async def test_get_subscription_items_filters_by_date() -> None:
    sub = mock_sub()
    sub.provider = SubscriptionProvider.RSS
    sub.external_data = {"feed_url": "https://example.com/feed.xml"}

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)
    rss_client_mock.get_feed_items.return_value = [
        RssFeedItem(
            title="Old Item",
            link="https://example.com/old",
            description="Old description",
            published=datetime(2020, 1, 1, tzinfo=timezone.utc),
            thumbnail="https://example.com/thumb.png",
            raw_data="",
        ),
        RssFeedItem(
            title="New Item",
            link="https://example.com/new",
            description="New description",
            published=datetime(2020, 1, 3, tzinfo=timezone.utc),
            thumbnail="https://example.com/thumb.png",
            raw_data="",
        ),
    ]
    rss_client_mock.get_feed_items_with_thumbnails.side_effect = lambda rss_items: rss_items

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    # Get items after Jan 2, 2020
    items = await service.get_subscription_items(
        sub.uuid,
        from_date=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )

    assert len(items) == 1
    assert items[0].name == "New Item"
    assert items[0].subscription_uuid == sub.uuid
    assert items[0].provider == ItemProvider.RSS
    assert str(items[0].url) == "https://example.com/new"


@pytest.mark.asyncio()
async def test_get_subscription_items_returns_empty_for_non_rss() -> None:
    sub = mock_sub()
    sub.provider = SubscriptionProvider.YOUTUBE

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    items = await service.get_subscription_items(
        sub.uuid,
        from_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )

    assert items == []


@pytest.mark.asyncio()
async def test_get_items_returns_empty_set() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    items = await service.get_items(item_ids={uuid4()})
    assert items == set()


@pytest.mark.asyncio()
async def test_get_subscription_from_url_creates_new_subscription() -> None:
    sub_repo = InMemorySubscriptionRepository()

    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)
    rss_client_mock.get_feed_info.return_value = RssFeedInfo(
        title="New Feed",
        link="https://example.com",
        description="New feed description",
        thumbnail="https://example.com/image.png",
        language="en",
    )

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    sub = await service.get_subscription_from_url(parse_url("https://example.com/feed.xml"))

    assert sub is not None
    assert sub.name == "New Feed"
    assert sub.provider == SubscriptionProvider.RSS
    assert sub.external_data["feed_url"] == "https://example.com/feed.xml"
    assert sub.external_data["language"] == "en"


@pytest.mark.asyncio()
async def test_get_subscription_from_url_updates_existing_subscription() -> None:
    existing_sub = mock_sub()
    existing_sub.provider = SubscriptionProvider.RSS
    existing_sub.url = parse_url("https://example.com/feed.xml")

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(existing_sub)

    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)
    rss_client_mock.get_feed_info.return_value = RssFeedInfo(
        title="Updated Title",
        link="https://example.com",
        description="Updated description",
        thumbnail="https://example.com/new-image.png",
        language="en",
    )

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    sub = await service.get_subscription_from_url(parse_url("https://example.com/feed.xml"))

    assert sub is not None
    assert sub.uuid == existing_sub.uuid  # Same subscription
    assert sub.name == "Updated Title"
    assert sub.description == "Updated description"


@pytest.mark.asyncio()
async def test_get_subscriptions_from_name_returns_empty_list() -> None:
    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()

    rss_client_mock = AsyncMock(spec=RssFeedClient)

    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=rss_client_mock,
        rss_data_repository=rss_data_repo,
    )

    subscriptions = await service.get_subscriptions_from_name("test")
    assert subscriptions == []
