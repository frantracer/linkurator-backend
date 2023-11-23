from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import floor
from typing import Optional, Any
from uuid import UUID

from pydantic.networks import AnyUrl

from linkurator_core.domain.common.units import Seconds

DEFAULT_ITEM_VERSION = 0


class ItemProvider(str, Enum):
    YOUTUBE = 'youtube'


@dataclass
class Item:
    uuid: UUID
    subscription_uuid: UUID
    name: str
    description: str
    url: AnyUrl
    thumbnail: AnyUrl
    duration: Optional[Seconds]
    version: int
    provider: ItemProvider
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
            published_at: datetime,
            duration: Optional[Seconds] = None,
            version: int = DEFAULT_ITEM_VERSION,
            provider: ItemProvider = ItemProvider.YOUTUBE) -> Item:
        now = datetime.now(tz=timezone.utc)
        return cls(
            uuid=uuid,
            subscription_uuid=subscription_uuid,
            name=name,
            description=description,
            url=url,
            duration=duration,
            thumbnail=thumbnail,
            created_at=now,
            updated_at=now,
            published_at=published_at.astimezone(timezone.utc),
            version=version,
            provider=provider)

    def __eq__(self, other: Any):
        if not isinstance(other, Item):
            return False
        return self.uuid == other.uuid and \
            self.subscription_uuid == other.subscription_uuid and \
            self.name == other.name and \
            self.description == other.description and \
            self.url == other.url and \
            self.thumbnail == other.thumbnail and \
            self.duration == other.duration and \
            self.version == other.version and \
            self.provider == other.provider and \
            int(self.created_at.timestamp() * 100) == floor(other.created_at.timestamp() * 100) and \
            int(self.updated_at.timestamp() * 100) == floor(other.updated_at.timestamp() * 100) and \
            int(self.published_at.timestamp() * 100) == floor(other.published_at.timestamp() * 100)

    def __hash__(self):
        return hash(self.uuid)
