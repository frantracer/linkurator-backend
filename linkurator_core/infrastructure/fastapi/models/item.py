from __future__ import annotations

from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema


class ItemSchema(BaseModel):
    """
    Content item that belongs to a subscription
    """
    uuid: UUID
    subscription_uuid: UUID
    subscription: SubscriptionSchema
    name: str
    description: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: Iso8601Datetime
    published_at: Iso8601Datetime
    duration: Optional[Seconds]

    recommended: bool
    discouraged: bool
    viewed: bool
    hidden: bool

    @classmethod
    def from_domain_item(
            cls,
            item: Item,
            subscription: Subscription,
            interactions: Optional[List[Interaction]] = None
    ) -> ItemSchema:
        recommended = False
        discouraged = False
        viewed = False
        hidden = False
        if interactions is not None:
            recommended = any(reaction.type == InteractionType.RECOMMENDED for reaction in interactions)
            discouraged = any(reaction.type == InteractionType.DISCOURAGED for reaction in interactions)
            viewed = any(reaction.type == InteractionType.VIEWED for reaction in interactions)
            hidden = any(reaction.type == InteractionType.HIDDEN for reaction in interactions)

        return cls(uuid=item.uuid,
                   subscription_uuid=item.subscription_uuid,
                   subscription=SubscriptionSchema.from_domain_subscription(subscription, None),
                   name=item.name,
                   description=item.description,
                   url=item.url,
                   thumbnail=item.thumbnail,
                   created_at=item.created_at,
                   published_at=item.published_at,
                   recommended=recommended,
                   discouraged=discouraged,
                   viewed=viewed,
                   hidden=hidden,
                   duration=item.duration)


class InteractionFilterSchema(Enum):
    """
    Filter items by interaction type
    """
    WITHOUT_INTERACTIONS = "without_interactions"
    RECOMMENDED = "recommended"
    DISCOURAGED = "discouraged"
    VIEWED = "viewed"
    HIDDEN = "hidden"


VALID_INTERACTIONS = ', '.join([value.value for value in InteractionFilterSchema])
