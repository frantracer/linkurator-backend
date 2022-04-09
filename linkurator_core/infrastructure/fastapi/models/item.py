from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl
from pydantic.main import BaseModel


class ItemSchema(BaseModel):
    """
    Content item that belongs to a subscription
    """
    uuid: UUID
    subscription_uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime

    def __init__(self, uuid: UUID, subscription_uuid: UUID, name: str, url: AnyUrl,
                 thumbnail: AnyUrl, created_at: datetime):
        super().__init__(uuid=uuid, subscription_uuid=subscription_uuid, name=name,
                         url=url, thumbnail=thumbnail, created_at=created_at)
