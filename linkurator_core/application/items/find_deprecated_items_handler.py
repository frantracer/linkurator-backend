from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.items.item_repository import ItemRepository


class FindDeprecatedItemsHandler:
    def __init__(self, item_repository: ItemRepository, event_bus: EventBusService):
        self.item_repository = item_repository
        self.event_bus = event_bus

    def execute(self) -> None:
        pass
