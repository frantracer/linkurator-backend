from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from uuid import UUID

from pydantic import AnyUrl


class SubscriptionProvider(str, Enum):
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"


@dataclass
class Subscription:
    uuid: UUID
    name: str
    provider: SubscriptionProvider
    external_data: Dict[str, str]
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime
    last_published_at: datetime

    @classmethod
    def new(cls, uuid: UUID, name: str, provider: SubscriptionProvider, url: AnyUrl, thumbnail: AnyUrl,
            external_data: Optional[Dict[str, str]] = None) -> Subscription:
        now = datetime.now(tz=timezone.utc)
        return cls(
            uuid=uuid,
            name=name,
            provider=provider,
            external_data=external_data or {},
            url=url,
            thumbnail=thumbnail,
            created_at=now,
            updated_at=now,
            scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
            last_published_at=datetime.fromtimestamp(0, tz=timezone.utc),
        )
