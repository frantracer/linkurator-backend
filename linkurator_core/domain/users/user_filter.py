from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class UserFilter:
    user_id: UUID
    text_filter: str | None
    min_duration: int | None
    max_duration: int | None
    include_items_without_interactions: bool
    include_recommended_items: bool
    include_discouraged_items: bool
    include_viewed_items: bool
    include_hidden_items: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(
        cls,
        user_id: UUID,
        text_filter: str | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
        include_items_without_interactions: bool = True,
        include_recommended_items: bool = True,
        include_discouraged_items: bool = True,
        include_viewed_items: bool = True,
        include_hidden_items: bool = True,
    ) -> UserFilter:
        now = datetime.now(timezone.utc)
        return cls(
            user_id=user_id,
            text_filter=text_filter,
            min_duration=min_duration,
            max_duration=max_duration,
            include_items_without_interactions=include_items_without_interactions,
            include_recommended_items=include_recommended_items,
            include_discouraged_items=include_discouraged_items,
            include_viewed_items=include_viewed_items,
            include_hidden_items=include_hidden_items,
            created_at=now,
            updated_at=now,
        )
