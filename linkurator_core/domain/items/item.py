from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import floor
from typing import Any, Callable
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.common.utils import datetime_now

DEFAULT_ITEM_VERSION = 0

type ItemProvider = str


@dataclass
class Item:
    uuid: UUID
    subscription_uuid: UUID
    name: str
    description: str
    url: AnyUrl
    thumbnail: AnyUrl
    duration: Seconds | None
    version: int
    provider: ItemProvider
    created_at: datetime
    updated_at: datetime
    published_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def new(
        cls,
        uuid: UUID,
        subscription_uuid: UUID,
        name: str,
        description: str,
        url: AnyUrl,
        thumbnail: AnyUrl,
        published_at: datetime,
        provider: ItemProvider,
        duration: Seconds | None = None,
        version: int = DEFAULT_ITEM_VERSION,
        deleted_at: datetime | None = None,
        now_function: Callable[[], datetime] = datetime_now,
    ) -> Item:
        now = now_function()
        published_at = min(published_at, now)

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
            published_at=published_at,
            version=version,
            provider=provider,
            deleted_at=deleted_at,
        )

    def __eq__(self, other: Any) -> bool:
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

    def __hash__(self) -> int:
        return hash(self.uuid)
