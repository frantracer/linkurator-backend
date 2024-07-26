from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl


@dataclass
class User:
    uuid: UUID
    first_name: str
    last_name: str
    username: str
    email: str
    avatar_url: AnyUrl
    locale: str
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime
    last_login_at: datetime
    google_refresh_token: Optional[str]
    subscription_uuids: List[UUID]
    is_admin: bool

    @classmethod
    def new(cls,
            uuid: UUID,
            first_name: str,
            last_name: str,
            username: str,
            email: str,
            avatar_url: AnyUrl,
            locale: str,
            google_refresh_token: Optional[str],
            subscription_uuids: Optional[List[UUID]] = None,
            is_admin: bool = False) -> User:
        now = datetime.now(timezone.utc)
        return cls(
            uuid=uuid,
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            avatar_url=avatar_url,
            locale=locale,
            created_at=now,
            updated_at=now,
            scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
            last_login_at=now,
            google_refresh_token=google_refresh_token,
            subscription_uuids=[] if subscription_uuids is None else subscription_uuids,
            is_admin=is_admin
        )
