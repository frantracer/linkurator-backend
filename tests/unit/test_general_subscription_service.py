from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import AnyUrl

from linkurator_core.domain.common.mock_factory import mock_item, mock_sub
from linkurator_core.domain.subscriptions.general_subscription_service import GeneralSubscriptionService
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


@pytest.mark.asyncio()
async def test_get_subscriptions_combines_results_from_all_services() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)

    sub1 = mock_sub(name="Sub1")
    sub2 = mock_sub(name="Sub2")
    sub3 = mock_sub(name="Sub3")

    service1.get_subscriptions.return_value = [sub1, sub2]
    service2.get_subscriptions.return_value = [sub3]

    general_service = GeneralSubscriptionService(services=[service1, service2])

    user_id = uuid4()
    result = await general_service.get_subscriptions(user_id=user_id, access_token="token")

    assert len(result) == 3
    assert sub1 in result
    assert sub2 in result
    assert sub3 in result


@pytest.mark.asyncio()
async def test_get_subscriptions_with_empty_services_list() -> None:
    general_service = GeneralSubscriptionService(services=[])

    result = await general_service.get_subscriptions(user_id=uuid4(), access_token="token")

    assert result == []


@pytest.mark.asyncio()
async def test_get_subscription_returns_first_non_none_result() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)
    service3 = AsyncMock(spec=SubscriptionService)

    sub = mock_sub(name="Found")

    service1.get_subscription.return_value = None
    service2.get_subscription.return_value = sub
    service3.get_subscription.return_value = mock_sub(name="Also Found")

    general_service = GeneralSubscriptionService(services=[service1, service2, service3])

    sub_id = uuid4()
    result = await general_service.get_subscription(sub_id=sub_id)

    assert result == sub


@pytest.mark.asyncio()
async def test_get_subscription_returns_none_when_all_services_return_none() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)

    service1.get_subscription.return_value = None
    service2.get_subscription.return_value = None

    general_service = GeneralSubscriptionService(services=[service1, service2])

    result = await general_service.get_subscription(sub_id=uuid4())

    assert result is None


@pytest.mark.asyncio()
async def test_get_items_unions_sets_from_all_services() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)

    item1 = mock_item()
    item2 = mock_item()
    item3 = mock_item()

    service1.get_items.return_value = {item1, item2}
    service2.get_items.return_value = {item2, item3}

    general_service = GeneralSubscriptionService(services=[service1, service2])

    item_ids = {item1.uuid, item2.uuid, item3.uuid}
    result = await general_service.get_items(item_ids=item_ids)

    assert len(result) == 3
    assert item1 in result
    assert item2 in result
    assert item3 in result


@pytest.mark.asyncio()
async def test_get_items_with_empty_services_list() -> None:
    general_service = GeneralSubscriptionService(services=[])

    result = await general_service.get_items(item_ids={uuid4()})

    assert result == set()


@pytest.mark.asyncio()
async def test_get_subscription_items_combines_lists_from_all_services() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)

    item1 = mock_item()
    item2 = mock_item()
    item3 = mock_item()

    service1.get_subscription_items.return_value = [item1]
    service2.get_subscription_items.return_value = [item2, item3]

    general_service = GeneralSubscriptionService(services=[service1, service2])

    sub_id = uuid4()
    from_date = datetime.now(tz=timezone.utc)
    result = await general_service.get_subscription_items(sub_id=sub_id, from_date=from_date)

    assert len(result) == 3
    assert item1 in result
    assert item2 in result
    assert item3 in result


@pytest.mark.asyncio()
async def test_get_subscription_from_url_returns_first_non_none_result() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)

    sub = mock_sub(name="Found from URL")

    service1.get_subscription_from_url.return_value = None
    service2.get_subscription_from_url.return_value = sub

    general_service = GeneralSubscriptionService(services=[service1, service2])

    url = AnyUrl("https://example.com/channel")
    result = await general_service.get_subscription_from_url(url=url)

    assert result == sub


@pytest.mark.asyncio()
async def test_get_subscription_from_url_returns_none_when_all_return_none() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)

    service1.get_subscription_from_url.return_value = None
    service2.get_subscription_from_url.return_value = None

    general_service = GeneralSubscriptionService(services=[service1, service2])

    url = AnyUrl("https://example.com/channel")
    result = await general_service.get_subscription_from_url(url=url)

    assert result is None


@pytest.mark.asyncio()
async def test_get_subscriptions_from_name_combines_lists_from_all_services() -> None:
    service1 = AsyncMock(spec=SubscriptionService)
    service2 = AsyncMock(spec=SubscriptionService)

    sub1 = mock_sub(name="Match1")
    sub2 = mock_sub(name="Match2")
    sub3 = mock_sub(name="Match3")

    service1.get_subscriptions_from_name.return_value = [sub1]
    service2.get_subscriptions_from_name.return_value = [sub2, sub3]

    general_service = GeneralSubscriptionService(services=[service1, service2])

    result = await general_service.get_subscriptions_from_name(name="Match")

    assert len(result) == 3
    assert sub1 in result
    assert sub2 in result
    assert sub3 in result


@pytest.mark.asyncio()
async def test_get_subscriptions_from_name_with_empty_services_list() -> None:
    general_service = GeneralSubscriptionService(services=[])

    result = await general_service.get_subscriptions_from_name(name="test")

    assert result == []
