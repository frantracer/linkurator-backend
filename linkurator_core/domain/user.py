from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    uuid: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
    google_refresh_token: str

    @classmethod
    def new(cls, uuid: UUID, name: str, email: str, google_refresh_token: str) -> User:
        now = datetime.now()
        return cls(
            uuid=uuid,
            name=name,
            email=email,
            created_at=now,
            updated_at=now,
            google_refresh_token=google_refresh_token
        )
