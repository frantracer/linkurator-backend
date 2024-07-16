from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class FollowedTopic:
    user_uuid: UUID
    topic_uuid: UUID
    created_at: datetime

    @classmethod
    def new(cls, user_uuid: UUID, topic_uuid: UUID) -> FollowedTopic:
        return cls(user_uuid, topic_uuid, datetime.now(timezone.utc))
