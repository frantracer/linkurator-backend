from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import List
from uuid import UUID


@dataclass
class Topic:
    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: List[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, uuid: UUID, name: str, user_id: UUID) -> Topic:
        return cls(uuid=uuid,
                   name=name,
                   user_id=user_id,
                   subscriptions_ids=[],
                   created_at=datetime.now(timezone.utc),
                   updated_at=datetime.now(timezone.utc))
