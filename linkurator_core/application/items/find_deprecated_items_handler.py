import logging

from linkurator_core.domain.common.event import ItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.items.item import YOUTUBE_ITEM_VERSION, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository


class FindDeprecatedItemsHandler:
    def __init__(self, item_repository: ItemRepository, event_bus: EventBusService) -> None:
        self.item_repository = item_repository
        self.event_bus = event_bus

    async def handle(self) -> None:
        logging.info("Finding deprecated items")

        items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(provider=ItemProvider.YOUTUBE, last_version=YOUTUBE_ITEM_VERSION),
            page_number=0,
            limit=50)

        if len(items) > 0:
            item_uuids = {item.uuid for item in items}
            await self.event_bus.publish(ItemsBecameOutdatedEvent.new(item_ids=item_uuids))
