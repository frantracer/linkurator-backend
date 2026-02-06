from dataclasses import dataclass

from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.user import User


@dataclass
class ItemWithInteractions:
    item: Item
    interactions: list[Interaction]

    def __post_init__(self) -> None:
        if any(i.item_uuid != self.item.uuid for i in self.interactions):
            msg = "All interactions must be for the same item"
            raise ValueError(msg)


@dataclass
class ItemWithInteractionsAndCurator:
    item: Item
    subscription: Subscription
    user_interactions: list[Interaction]
    curator_interactions: list[Interaction]
    curator: User | None
