from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic.networks import AnyUrl


@dataclass
class Subscription:
    uuid: UUID
    name: str
    provider: str
    external_id: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime

    @classmethod
    def new(cls, uuid: UUID, name: str, provider: str, external_id: str, url: AnyUrl, thumbnail: AnyUrl):
        now = datetime.now()
        return cls(
            uuid=uuid,
            name=name,
            provider=provider,
            external_id=external_id,
            url=url,
            thumbnail=thumbnail,
            created_at=now,
            updated_at=now,
            scanned_at=datetime.fromtimestamp(0)
        )
