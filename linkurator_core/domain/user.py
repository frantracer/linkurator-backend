from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class User:
    uuid: UUID
    first_name: str
    last_name: str
    email: str
    created_at: datetime
    updated_at: datetime
    google_refresh_token: Optional[str]

    @classmethod
    def new(cls, uuid: UUID, first_name: str, last_name: str, email: str, google_refresh_token: Optional[str]) -> User:
        now = datetime.now()
        return cls(
            uuid=uuid,
            first_name=first_name,
            last_name=last_name,
            email=email,
            created_at=now,
            updated_at=now,
            google_refresh_token=google_refresh_token
        )
