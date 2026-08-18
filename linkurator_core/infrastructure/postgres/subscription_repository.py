from __future__ import annotations

import json
from datetime import datetime
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.items.item import ItemProvider
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionFilterCriteria,
    SubscriptionRepository,
)
from linkurator_core.infrastructure.postgres.common import PostgresConnector


def _row_to_domain(row: Any) -> Subscription:
    return Subscription(
        uuid=row["uuid"],
        name=row["name"],
        provider=row["provider"],
        external_data=row["external_data"],
        url=AnyUrl(row["url"]),
        thumbnail=AnyUrl(row["thumbnail"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        scanned_at=row["scanned_at"],
        last_published_at=row["last_published_at"],
        description=row["description"],
        summary=row["summary"],
    )


class PostgresSubscriptionRepository(SubscriptionRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def add(self, subscription: Subscription) -> None:
        pool = await self._connector.pool()
        await pool.execute(
            """
            INSERT INTO subscriptions (
                uuid, name, provider, external_data, url, thumbnail,
                created_at, updated_at, scanned_at, last_published_at, description, summary
            ) VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            subscription.uuid, subscription.name, subscription.provider,
            json.dumps(subscription.external_data), str(subscription.url), str(subscription.thumbnail),
            subscription.created_at, subscription.updated_at, subscription.scanned_at,
            subscription.last_published_at, subscription.description, subscription.summary,
        )

    async def get(self, subscription_id: UUID) -> Subscription | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM subscriptions WHERE uuid = %s", subscription_id)
        return None if row is None else _row_to_domain(row)

    async def get_list(self, subscription_ids: list[UUID]) -> list[Subscription]:
        pool = await self._connector.pool()
        rows = await pool.fetch(
            "SELECT * FROM subscriptions WHERE uuid = ANY(%s::uuid[]) ORDER BY created_at DESC",
            subscription_ids,
        )
        return [_row_to_domain(row) for row in rows]

    async def delete(self, subscription_id: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM subscriptions WHERE uuid = %s", subscription_id)

    async def delete_all(self) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM subscriptions")

    async def update(self, subscription: Subscription) -> None:
        pool = await self._connector.pool()
        await pool.execute(
            """
            UPDATE subscriptions SET
                name = %s, provider = %s, external_data = %s::jsonb, url = %s, thumbnail = %s,
                created_at = %s, updated_at = %s, scanned_at = %s, last_published_at = %s,
                description = %s, summary = %s
            WHERE uuid = %s
            """,
            subscription.name, subscription.provider,
            json.dumps(subscription.external_data), str(subscription.url), str(subscription.thumbnail),
            subscription.created_at, subscription.updated_at, subscription.scanned_at,
            subscription.last_published_at, subscription.description, subscription.summary,
            subscription.uuid,
        )

    async def find_by_url(self, url: AnyUrl) -> Subscription | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM subscriptions WHERE url = %s", str(url))
        return None if row is None else _row_to_domain(row)

    async def find_latest_scan_before(
            self, datetime_limit: datetime, provider: ItemProvider | None = None,
    ) -> list[Subscription]:
        pool = await self._connector.pool()
        if provider is None:
            rows = await pool.fetch(
                "SELECT * FROM subscriptions WHERE scanned_at < %s ORDER BY scanned_at DESC",
                datetime_limit,
            )
        else:
            rows = await pool.fetch(
                "SELECT * FROM subscriptions WHERE scanned_at < %s AND provider = %s ORDER BY scanned_at DESC",
                datetime_limit, provider,
            )
        return [_row_to_domain(row) for row in rows]

    async def find_by_name(self, name: str, provider: ItemProvider | None = None) -> list[Subscription]:
        pool = await self._connector.pool()
        if provider is None:
            rows = await pool.fetch(
                """
                SELECT * FROM subscriptions
                WHERE to_tsvector('simple', immutable_unaccent(name))
                    @@ plainto_tsquery('simple', immutable_unaccent(%s))
                ORDER BY created_at DESC
                """,
                name,
            )
        else:
            rows = await pool.fetch(
                """
                SELECT * FROM subscriptions
                WHERE to_tsvector('simple', immutable_unaccent(name))
                    @@ plainto_tsquery('simple', immutable_unaccent(%s))
                    AND provider = %s
                ORDER BY created_at DESC
                """,
                name, provider,
            )
        return [_row_to_domain(row) for row in rows]

    async def find(self, criteria: SubscriptionFilterCriteria) -> list[Subscription]:
        pool = await self._connector.pool()
        conditions: list[str] = []
        params: list[Any] = []
        if criteria.updated_before is not None:
            params.append(criteria.updated_before)
            conditions.append("updated_at < %s")
        if criteria.has_summary is not None:
            conditions.append("summary != ''" if criteria.has_summary else "summary = ''")

        query = "SELECT * FROM subscriptions"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC"

        rows = await pool.fetch(query, *params)
        return [_row_to_domain(row) for row in rows]

    async def count_subscriptions(self, provider: ItemProvider | None = None) -> int:
        pool = await self._connector.pool()
        if provider is None:
            return await pool.fetchval("SELECT COUNT(*) FROM subscriptions")
        return await pool.fetchval("SELECT COUNT(*) FROM subscriptions WHERE provider = %s", provider)
