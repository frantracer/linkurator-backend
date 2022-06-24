from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID


@dataclass
class User:
    uuid: UUID
    first_name: str
    last_name: str
    email: str
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime
    google_refresh_token: Optional[str]
    subscription_uuids: List[UUID]

    @classmethod
    def new(cls,
            uuid: UUID,
            first_name: str,
            last_name: str,
            email: str,
            google_refresh_token: Optional[str],
            subscription_uuids: Optional[List[UUID]] = None) -> User:
        now = datetime.now()
        return cls(
            uuid=uuid,
            first_name=first_name,
            last_name=last_name,
            email=email,
            created_at=now,
            updated_at=now,
            scanned_at=datetime.fromtimestamp(0),
            google_refresh_token=google_refresh_token,
            subscription_uuids=[] if subscription_uuids is None else subscription_uuids
        )
