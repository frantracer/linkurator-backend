from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic.networks import AnyUrl


@dataclass
class Item:
    uuid: UUID
    subscription_uuid: UUID
    name: str
    description: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    published_at: datetime

    @classmethod
    def new(cls, uuid: UUID,
            subscription_uuid: UUID,
            name: str,
            description: str,
            url: AnyUrl,
            thumbnail: AnyUrl,
            published_at: datetime):
        now = datetime.now()
        return cls(
            uuid=uuid,
            subscription_uuid=subscription_uuid,
            name=name,
            description=description,
            url=url,
            thumbnail=thumbnail,
            created_at=now,
            updated_at=now,
            published_at=published_at)
