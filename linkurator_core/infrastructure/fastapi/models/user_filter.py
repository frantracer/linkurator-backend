from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from linkurator_core.domain.users.user_filter import UserFilter
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class UserFilterSchema(BaseModel):
    """User filter schema for API responses."""

    user_id: UUID
    text_filter: str | None = None
    min_duration: int | None = None
    max_duration: int | None = None
    include_items_without_interactions: bool = True
    include_recommended_items: bool = True
    include_discouraged_items: bool = True
    include_viewed_items: bool = True
    include_hidden_items: bool = True
    created_at: Iso8601Datetime
    updated_at: Iso8601Datetime

    @classmethod
    def from_domain(cls, user_filter: UserFilter) -> UserFilterSchema:
        return cls(
            user_id=user_filter.user_id,
            text_filter=user_filter.text_filter,
            min_duration=user_filter.min_duration,
            max_duration=user_filter.max_duration,
            include_items_without_interactions=user_filter.include_items_without_interactions,
            include_recommended_items=user_filter.include_recommended_items,
            include_discouraged_items=user_filter.include_discouraged_items,
            include_viewed_items=user_filter.include_viewed_items,
            include_hidden_items=user_filter.include_hidden_items,
            created_at=user_filter.created_at,
            updated_at=user_filter.updated_at,
        )


class UpsertUserFilterRequest(BaseModel):
    """Request schema for upserting user filter."""

    text_filter: str | None = None
    min_duration: int | None = None
    max_duration: int | None = None
    include_items_without_interactions: bool = True
    include_recommended_items: bool = True
    include_discouraged_items: bool = True
    include_viewed_items: bool = True
    include_hidden_items: bool = True
    excluded_subscriptions: list[UUID] = []
