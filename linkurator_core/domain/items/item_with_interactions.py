from dataclasses import dataclass
from typing import List

from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item import Item


@dataclass
class ItemWithInteractions:
    item: Item
    interactions: List[Interaction]

    def __post_init__(self) -> None:
        if any(i.item_uuid != self.item.uuid for i in self.interactions):
            msg = "All interactions must be for the same item"
            raise ValueError(msg)
