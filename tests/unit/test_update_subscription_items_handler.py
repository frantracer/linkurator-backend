import asyncio
import uuid
from copy import copy
from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from linkurator_core.application.subscriptions.update_subscription_items_handler import UpdateSubscriptionItemsHandler
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.infrastructure.asyncio.utils import run_parallel


@pytest.mark.asyncio
async def test_update_subscriptions_items_with_an_item_that_is_not_registered():
    sub1 = Subscription(
        uuid=uuid.UUID("b6cae596-4526-4ab7-b5da-bd803f04980b"),
        name="sub1",
        provider=SubscriptionProvider.YOUTUBE,
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(1, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(2, tz=timezone.utc),
        external_data={})

    item1 = Item.new(
        uuid=uuid.UUID("64ad0bbb-27d5-4b45-bc9b-d3a09c1d8df2"),
        name="item1",
        description="",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        subscription_uuid=sub1.uuid,
        published_at=datetime.fromtimestamp(0, tz=timezone.utc))

    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_service.get_subscription_items.return_value = [item1]

    subscription_repository = MagicMock(spec=SubscriptionRepository)
    subscription_repository.get.return_value = copy(sub1)

    item_repository = MagicMock(spec=ItemRepository)
    item_repository.find_items.return_value = ([], 0)

    handler = UpdateSubscriptionItemsHandler(subscription_service=subscription_service,
                                             subscription_repository=subscription_repository,
                                             item_repository=item_repository)

    await handler.handle(sub1.uuid)

    assert subscription_service.get_subscription_items.call_count == 1
    assert subscription_service.get_subscription_items.call_args == call(sub_id=sub1.uuid, from_date=sub1.scanned_at)
    assert subscription_repository.get.call_count == 1
    assert subscription_repository.get.call_args == call(sub1.uuid)
    assert item_repository.find_items.call_count == 1
    assert item_repository.upsert_bulk.call_count == 1
    assert item_repository.upsert_bulk.call_args == call([item1])
    assert subscription_repository.update.call_count == 1
    updated_sub = subscription_repository.update.call_args[0][0]
    assert updated_sub.scanned_at > sub1.scanned_at


@pytest.mark.asyncio
async def test_update_subscriptions_items_with_items_that_are_already_registered():
    sub1 = Subscription(
        uuid=uuid.UUID("b6cae596-4526-4ab7-b5da-bd803f04980b"),
        name="sub1",
        provider=SubscriptionProvider.YOUTUBE,
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(1, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(2, tz=timezone.utc),
        external_data={})

    item1 = Item.new(
        uuid=uuid.UUID("64ad0bbb-27d5-4b45-bc9b-d3a09c1d8df2"),
        name="item1",
        description="",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        subscription_uuid=sub1.uuid,
        published_at=datetime.fromtimestamp(0, tz=timezone.utc))

    item2 = Item.new(
        uuid=uuid.UUID("64ad0bbb-27d5-4b45-bc9b-d3a09c1d8df3"),
        name="item2",
        description="",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        subscription_uuid=sub1.uuid,
        published_at=datetime.fromtimestamp(0, tz=timezone.utc))

    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_service.get_subscription_items.return_value = [item1]

    subscription_repository = MagicMock(spec=SubscriptionRepository)
    subscription_repository.get.return_value = copy(sub1)

    item_repository = MagicMock(spec=ItemRepository)
    item_repository.find_items.return_value = ([item2], 1)

    handler = UpdateSubscriptionItemsHandler(subscription_service=subscription_service,
                                             subscription_repository=subscription_repository,
                                             item_repository=item_repository)

    await handler.handle(sub1.uuid)

    assert subscription_service.get_subscription_items.call_count == 1
    assert subscription_service.get_subscription_items.call_args == call(sub_id=sub1.uuid, from_date=sub1.scanned_at)
    assert subscription_repository.get.call_count == 1
    assert subscription_repository.get.call_args == call(sub1.uuid)
    assert item_repository.find_items.call_count == 1
    assert item_repository.find_items.call_args == call(
        criteria=ItemFilterCriteria(url=item1.url),
        page_number=0,
        limit=1)
    assert item_repository.upsert_bulk.call_count == 1
    assert item_repository.upsert_bulk.call_args == call([])
    assert subscription_repository.update.call_count == 1
    updated_sub = subscription_repository.update.call_args[0][0]
    assert updated_sub.scanned_at > sub1.scanned_at


@pytest.mark.asyncio
async def test_only_one_concurrent_update_is_allowed_to_run_per_subscription():
    sub1 = Subscription(
        uuid=uuid.UUID("547d692c-d2a2-49ef-bfd6-97cb02fb03d1"),
        name="sub1",
        provider=SubscriptionProvider.YOUTUBE,
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(1, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(2, tz=timezone.utc),
        external_data={})

    async def wait_1_second_and_return_no_items(
            sub_id: uuid.UUID, from_date: datetime) -> List[Item]:  # pylint: disable=unused-argument
        await asyncio.sleep(1)
        return []

    subscription_service = AsyncMock(spec=SubscriptionService)
    subscription_service.get_subscription_items.side_effect = wait_1_second_and_return_no_items

    subscription_repository = MagicMock(spec=SubscriptionRepository)
    subscription_repository.get.return_value = copy(sub1)

    item_repository = MagicMock(spec=ItemRepository)

    handler = UpdateSubscriptionItemsHandler(subscription_service=subscription_service,
                                             subscription_repository=subscription_repository,
                                             item_repository=item_repository)
    await run_parallel(
        handler.handle(sub1.uuid),
        handler.handle(sub1.uuid))

    await handler.handle(sub1.uuid)

    assert subscription_repository.update.call_count == 2
