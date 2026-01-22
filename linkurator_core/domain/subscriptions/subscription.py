from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.common.utils import datetime_now
from linkurator_core.domain.items.item import ItemProvider


class Subscription(BaseModel):
    uuid: UUID
    name: str
    provider: ItemProvider
    external_data: dict[str, str]
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime
    last_published_at: datetime
    description: str
    summary: str

    @classmethod
    def new(cls,
            uuid: UUID,
            name: str,
            provider: ItemProvider,
            url: AnyUrl,
            thumbnail: AnyUrl,
            description: str,
            external_data: dict[str, str] | None = None,
            summary: str | None = None,
            ) -> Subscription:
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
            description=description,
            summary=summary or "",
        )

    def update_summary(self, summary: str, now_function: Callable[[], datetime] = datetime_now) -> None:
        self.summary = summary
        self.updated_at = now_function()
