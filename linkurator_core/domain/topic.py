from dataclasses import dataclass
from datetime import datetime
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
