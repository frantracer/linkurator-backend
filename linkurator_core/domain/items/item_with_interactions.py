from dataclasses import dataclass, field

from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.user import User


@dataclass
class ItemWithInteractions:
    item: Item
    subscription: Subscription
    interactions: list[Interaction]
    curator_interactions: list[Interaction] = field(default_factory=list)
    curator: User | None = None

    def __post_init__(self) -> None:
        if any(i.item_uuid != self.item.uuid for i in self.interactions):
            msg = "All interactions must be for the same item"
            raise ValueError(msg)

        if any(i.item_uuid != self.item.uuid for i in self.curator_interactions):
            msg = "All curator interactions must be for the same item"
            raise ValueError(msg)
