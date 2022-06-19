from copy import copy
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call
import uuid

import pytest

from linkurator_core.application.update_subscription_items_handler import UpdateSubscriptionItemsHandler
from linkurator_core.common.utils import parse_url
from linkurator_core.domain.item import Item
from linkurator_core.domain.subscription import Subscription


@pytest.mark.asyncio
async def test_update_subscriptions_items_with_a_items_that_are_not_registered():
    sub1 = Subscription(
        uuid=uuid.UUID("b6cae596-4526-4ab7-b5da-bd803f04980b"),
        name="sub1",
        provider="myprovider",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        created_at=datetime.fromtimestamp(0),
        updated_at=datetime.fromtimestamp(1),
        scanned_at=datetime.fromtimestamp(2),
        external_data={})

    item1 = Item.new(
        uuid=uuid.UUID("64ad0bbb-27d5-4b45-bc9b-d3a09c1d8df2"),
        name="item1",
        description="",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        subscription_uuid=sub1.uuid,
        published_at=datetime.fromtimestamp(0))

    subscription_service = AsyncMock()
    subscription_service.get_items.return_value = [item1]

    subscription_repository = MagicMock()
    subscription_repository.get.return_value = copy(sub1)

    item_repository = MagicMock()
    item_repository.find.return_value = None

    handler = UpdateSubscriptionItemsHandler(subscription_service=subscription_service,
                                             subscription_repository=subscription_repository,
                                             item_repository=item_repository)

    await handler.handle(sub1.uuid)

    assert subscription_service.get_items.call_count == 1
    assert subscription_service.get_items.call_args == call(sub_id=sub1.uuid, from_date=sub1.scanned_at)
    assert subscription_repository.get.call_count == 1
    assert subscription_repository.get.call_args == call(sub1.uuid)
    assert item_repository.find.call_count == 1
    assert item_repository.add.call_count == 1
    assert item_repository.add.call_args == call(item1)
    assert subscription_repository.update.call_count == 1
    updated_sub = subscription_repository.update.call_args[0][0]
    assert updated_sub.scanned_at > sub1.scanned_at


@pytest.mark.asyncio
async def test_update_subscriptions_items_with_a_items_that_are_already_registered():
    sub1 = Subscription(
        uuid=uuid.UUID("b6cae596-4526-4ab7-b5da-bd803f04980b"),
        name="sub1",
        provider="myprovider",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        created_at=datetime.fromtimestamp(0),
        updated_at=datetime.fromtimestamp(1),
        scanned_at=datetime.fromtimestamp(2),
        external_data={})

    item1 = Item.new(
        uuid=uuid.UUID("64ad0bbb-27d5-4b45-bc9b-d3a09c1d8df2"),
        name="item1",
        description="",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        subscription_uuid=sub1.uuid,
        published_at=datetime.fromtimestamp(0))

    item2 = Item.new(
        uuid=uuid.UUID("64ad0bbb-27d5-4b45-bc9b-d3a09c1d8df3"),
        name="item2",
        description="",
        url=parse_url("http://url.com"),
        thumbnail=parse_url("http://thumbnail.com"),
        subscription_uuid=sub1.uuid,
        published_at=datetime.fromtimestamp(0))

    subscription_service = AsyncMock()
    subscription_service.get_items.return_value = [item1]

    subscription_repository = MagicMock()
    subscription_repository.get.return_value = copy(sub1)

    item_repository = MagicMock()
    item_repository.find.return_value = item2

    handler = UpdateSubscriptionItemsHandler(subscription_service=subscription_service,
                                             subscription_repository=subscription_repository,
                                             item_repository=item_repository)

    await handler.handle(sub1.uuid)

    assert subscription_service.get_items.call_count == 1
    assert subscription_service.get_items.call_args == call(sub_id=sub1.uuid, from_date=sub1.scanned_at)
    assert subscription_repository.get.call_count == 1
    assert subscription_repository.get.call_args == call(sub1.uuid)
    assert item_repository.find.call_count == 1
    assert item_repository.find.call_args == call(item1)
    assert item_repository.add.call_count == 0
    assert subscription_repository.update.call_count == 1
    updated_sub = subscription_repository.update.call_args[0][0]
    assert updated_sub.scanned_at > sub1.scanned_at
