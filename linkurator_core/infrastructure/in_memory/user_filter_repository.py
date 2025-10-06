from __future__ import annotations

from copy import copy
from datetime import datetime, timezone
from uuid import UUID

from linkurator_core.domain.users.user_filter import UserFilter
from linkurator_core.domain.users.user_filter_repository import UserFilterRepository


class InMemoryUserFilterRepository(UserFilterRepository):
    def __init__(self) -> None:
        super().__init__()
        self.filters: dict[UUID, UserFilter] = {}

    async def get(self, user_id: UUID) -> UserFilter | None:
        return copy(self.filters.get(user_id))

    async def upsert(self, user_filter: UserFilter) -> None:
        user_filter.updated_at = datetime.now(timezone.utc)
        self.filters[user_filter.user_id] = user_filter

    async def delete(self, user_id: UUID) -> None:
        if user_id in self.filters:
            del self.filters[user_id]

    async def delete_all(self) -> None:
        self.filters = {}
