from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl
from pydantic.main import BaseModel

from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item


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
    created_at: datetime
    published_at: datetime
    duration: Optional[Seconds]

    recommended: bool
    discouraged: bool
    viewed: bool
    hidden: bool

    def __init__(self, uuid: UUID, subscription_uuid: UUID, name: str, description: str, url: AnyUrl,
                 thumbnail: AnyUrl, created_at: datetime, published_at: datetime, duration: Optional[Seconds],
                 recommended: bool = False, discouraged: bool = False,
                 viewed: bool = False, hidden: bool = False):
        super().__init__(uuid=uuid, subscription_uuid=subscription_uuid, name=name, description=description,
                         url=url, thumbnail=thumbnail, created_at=created_at, published_at=published_at,
                         recommended=recommended,
                         discouraged=discouraged,
                         viewed=viewed,
                         hidden=hidden,
                         duration=duration)

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
