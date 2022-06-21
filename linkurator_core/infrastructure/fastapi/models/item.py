from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl
from pydantic.main import BaseModel

from linkurator_core.domain.item import Item


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

    def __init__(self, uuid: UUID, subscription_uuid: UUID, name: str, description: str, url: AnyUrl,
                 thumbnail: AnyUrl, created_at: datetime, published_at: datetime):
        super().__init__(uuid=uuid, subscription_uuid=subscription_uuid, name=name, description=description,
                         url=url, thumbnail=thumbnail, created_at=created_at, published_at=published_at)

    @classmethod
    def from_domain_item(cls, item: Item) -> ItemSchema:
        return cls(uuid=item.uuid,
                   subscription_uuid=item.subscription_uuid,
                   name=item.name,
                   description=item.description,
                   url=item.url,
                   thumbnail=item.thumbnail,
                   created_at=item.created_at,
                   published_at=item.published_at)
