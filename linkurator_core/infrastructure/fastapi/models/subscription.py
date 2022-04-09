from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl
from pydantic.main import BaseModel


class SubscriptionSchema(BaseModel):
    """
    Information about the different channels the user is subscribed to
    """
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    scanned_at: datetime

    def __init__(self, uuid: UUID, name: str, url: AnyUrl, thumbnail: AnyUrl,
                 created_at: datetime, scanned_at: datetime):
        super().__init__(uuid=uuid, name=name, url=url, thumbnail=thumbnail,
                         created_at=created_at, scanned_at=scanned_at)
