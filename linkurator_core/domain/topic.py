from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
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
    def new(cls,
            uuid: UUID,
            name: str,
            user_id: UUID,
            subscription_ids: Optional[List[UUID]] = None
            ) -> Topic:
        return cls(uuid=uuid,
                   name=name,
                   user_id=user_id,
                   subscriptions_ids=[] if subscription_ids is None else subscription_ids,
                   created_at=datetime.now(timezone.utc),
                   updated_at=datetime.now(timezone.utc))

    def add_subscription(self, subscription_id: UUID) -> None:
        self.subscriptions_ids.append(subscription_id)
        self.updated_at = datetime.now(timezone.utc)

    def remove_subscription(self, subscription_id: UUID) -> None:
        if subscription_id in self.subscriptions_ids:
            self.subscriptions_ids.remove(subscription_id)
            self.updated_at = datetime.now(timezone.utc)
