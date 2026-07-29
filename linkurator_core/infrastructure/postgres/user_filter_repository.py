from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

from linkurator_core.domain.users.user_filter import UserFilter
from linkurator_core.domain.users.user_filter_repository import UserFilterRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector


def _row_to_domain(row: Any) -> UserFilter:
    return UserFilter(
        user_id=row["user_id"],
        text_filter=row["text_filter"],
        min_duration=row["min_duration"],
        max_duration=row["max_duration"],
        include_items_without_interactions=row["include_items_without_interactions"],
        include_recommended_items=row["include_recommended_items"],
        include_discouraged_items=row["include_discouraged_items"],
        include_viewed_items=row["include_viewed_items"],
        include_hidden_items=row["include_hidden_items"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresUserFilterRepository(UserFilterRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def get(self, user_id: UUID) -> UserFilter | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM user_filters WHERE user_id = %s", user_id)
        if row is None:
            return None
        return _row_to_domain(row)

    async def upsert(self, user_filter: UserFilter) -> None:
        user_filter.updated_at = datetime.now(timezone.utc)
        pool = await self._connector.pool()
        await pool.execute(
            """
            INSERT INTO user_filters (
                user_id, text_filter, min_duration, max_duration,
                include_items_without_interactions, include_recommended_items,
                include_discouraged_items, include_viewed_items, include_hidden_items,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                text_filter = EXCLUDED.text_filter,
                min_duration = EXCLUDED.min_duration,
                max_duration = EXCLUDED.max_duration,
                include_items_without_interactions = EXCLUDED.include_items_without_interactions,
                include_recommended_items = EXCLUDED.include_recommended_items,
                include_discouraged_items = EXCLUDED.include_discouraged_items,
                include_viewed_items = EXCLUDED.include_viewed_items,
                include_hidden_items = EXCLUDED.include_hidden_items,
                updated_at = EXCLUDED.updated_at
            """,
            user_filter.user_id,
            user_filter.text_filter,
            user_filter.min_duration,
            user_filter.max_duration,
            user_filter.include_items_without_interactions,
            user_filter.include_recommended_items,
            user_filter.include_discouraged_items,
            user_filter.include_viewed_items,
            user_filter.include_hidden_items,
            user_filter.created_at,
            user_filter.updated_at,
        )

    async def delete(self, user_id: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM user_filters WHERE user_id = %s", user_id)

    async def delete_all(self) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM user_filters")
