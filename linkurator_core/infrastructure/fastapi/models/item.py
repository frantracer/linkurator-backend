from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class ItemSchema(BaseModel):
    """
    Content item that belongs to a subscription
    """
    uuid: UUID
    subscription_uuid: UUID
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
    def from_domain_item(cls, item: Item, interactions: Optional[List[Interaction]] = None) -> ItemSchema:
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
