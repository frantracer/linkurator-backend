from dataclasses import dataclass
from typing import List

from linkurator_core.domain.interaction import Interaction
from linkurator_core.domain.item import Item


@dataclass
class ItemWithInteractions:
    item: Item
    interactions: List[Interaction]

    def __post_init__(self):
        if any(i.item_uuid != self.item.uuid for i in self.interactions):
            raise ValueError("All interactions must be for the same item")
