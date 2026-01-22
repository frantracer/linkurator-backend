import logging

from linkurator_core.domain.common.event import ItemsBecameOutdatedEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


class FindDeprecatedItemsHandler:
    def __init__(
        self,
        item_repository: ItemRepository,
        event_bus: EventBusService,
        subscription_services: list[SubscriptionService],
    ) -> None:
        self.item_repository = item_repository
        self.event_bus = event_bus
        self.subscription_services = subscription_services

    async def handle(self) -> None:
        logging.info("Finding deprecated items")

        for service in self.subscription_services:
            items = await self.item_repository.find_items(
                criteria=ItemFilterCriteria(
                    provider=service.provider_name(),
                    last_version=service.provider_version()),
                page_number=0,
                limit=50)

            if len(items) > 0:
                item_uuids = {item.uuid for item in items}
                await self.event_bus.publish(ItemsBecameOutdatedEvent.new(item_ids=item_uuids))
