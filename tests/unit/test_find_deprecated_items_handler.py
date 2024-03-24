from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from linkurator_core.application.items.find_deprecated_items_handler import FindDeprecatedItemsHandler
from linkurator_core.domain.common.event import ItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.item import ItemProvider, YOUTUBE_ITEM_VERSION
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria


@pytest.mark.asyncio
async def test_find_deprecated_items_publish_an_event_with_all_deprecated_items() -> None:
    item_repository = MagicMock(spec=ItemRepository)
    event_bus = MagicMock(spec=EventBusService)
    find_deprecated_items_handler = FindDeprecatedItemsHandler(item_repository, event_bus)

    items = [mock_item(item_uuid=uuid4()),
             mock_item(item_uuid=uuid4())]

    item_repository.find_items.return_value = items

    await find_deprecated_items_handler.handle()

    item_repository.find_items.assert_called_once_with(
        criteria=ItemFilterCriteria(provider=ItemProvider.YOUTUBE, last_version=YOUTUBE_ITEM_VERSION),
        page_number=0,
        limit=50)
    event_bus.publish.assert_called_once_with(
        ItemsBecameOutdatedEvent.new(item_ids={items[0].uuid, items[1].uuid}))


@pytest.mark.asyncio
async def test_find_deprecated_items_does_not_publish_an_event_if_there_are_no_deprecated_items() -> None:
    item_repository = MagicMock(spec=ItemRepository)
    event_bus = MagicMock(spec=EventBusService)
    find_deprecated_items_handler = FindDeprecatedItemsHandler(item_repository, event_bus)

    item_repository.find_items.return_value = []

    await find_deprecated_items_handler.handle()

    event_bus.publish.assert_not_called()
