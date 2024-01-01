from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID


class InteractionType(str, Enum):
    RECOMMENDED = "recommended"
    DISCOURAGED = "discouraged"
    VIEWED = "viewed"
    HIDDEN = "hidden"


@dataclass
class Interaction:
    uuid: UUID
    item_uuid: UUID
    user_uuid: UUID
    type: InteractionType
    created_at: datetime

    @classmethod
    def new(cls, uuid: UUID, item_uuid: UUID, user_uuid: UUID, interaction_type: InteractionType) -> Interaction:
        now = datetime.now(tz=timezone.utc)
        return cls(
            uuid=uuid,
            item_uuid=item_uuid,
            user_uuid=user_uuid,
            type=interaction_type,
            created_at=now)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Interaction):
            return False
        return self.uuid == other.uuid

    def __hash__(self) -> int:
        return hash(self.uuid)
