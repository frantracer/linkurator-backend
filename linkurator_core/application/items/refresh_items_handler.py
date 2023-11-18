from typing import List

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository


class RefreshItemsHandler:
    def __init__(self, item_repository: ItemRepository):
        self.item_repository = item_repository

    def handle(self, items: List[Item]) -> None:
        pass
