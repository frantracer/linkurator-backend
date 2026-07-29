from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

from linkurator_core.domain.common import utils
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import InteractionFilterCriteria, ItemFilterCriteria, ItemRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector


def _row_to_item(row: Any) -> Item:
    return Item(
        uuid=row["uuid"],
        subscription_uuid=row["subscription_uuid"],
        name=row["name"],
        description=row["description"],
        url=utils.parse_url(row["url"]),
        thumbnail=utils.parse_url(row["thumbnail"]),
        duration=row["duration"],
        version=row["version"],
        provider=row["provider"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row["published_at"],
        deleted_at=row["deleted_at"],
    )


def _row_to_interaction(row: Any) -> Interaction:
    return Interaction(
        uuid=row["uuid"],
        item_uuid=row["item_uuid"],
        user_uuid=row["user_uuid"],
        type=InteractionType(row["type"]),
        created_at=row["created_at"],
    )


@dataclass(frozen=True)
class SqlFragment:
    """A piece of SQL text with placeholders (%s) paired with the parameter values"""

    placeholders: str
    params: tuple[Any, ...] = ()


def _comparison(column: str, operator: str, value: Any) -> SqlFragment:
    return SqlFragment(f"{column} {operator} %s", (value,))


def _uuid_array_condition(column: str, values: Sequence[UUID]) -> SqlFragment:
    return SqlFragment(f"{column} = ANY(%s::uuid[])", (list(values),))


def _text_search_condition(column: str, text: str) -> SqlFragment:
    return SqlFragment(
        f"to_tsvector('simple', immutable_unaccent({column})) "
        "@@ plainto_tsquery('simple', immutable_unaccent(%s))",
        (text,),
    )


def _join(fragments: Sequence[SqlFragment], separator: str) -> SqlFragment:
    return SqlFragment(
        separator.join(fragment.placeholders for fragment in fragments),
        tuple(value for fragment in fragments for value in fragment.params),
    )


def _build_item_conditions(criteria: ItemFilterCriteria) -> list[SqlFragment]:
    fragments = [SqlFragment("deleted_at IS NULL")]
    if criteria.item_ids is not None:
        fragments.append(_uuid_array_condition("uuid", list(criteria.item_ids)))
    if criteria.subscription_ids is not None:
        fragments.append(_uuid_array_condition("subscription_uuid", list(criteria.subscription_ids)))
    if criteria.published_after is not None:
        fragments.append(_comparison("published_at", ">", criteria.published_after))
    if criteria.created_before is not None:
        fragments.append(_comparison("created_at", "<", criteria.created_before))
    if criteria.updated_before is not None:
        fragments.append(_comparison("updated_at", "<", criteria.updated_before))
    if criteria.url is not None:
        fragments.append(_comparison("url", "=", str(criteria.url)))
    if criteria.last_version is not None:
        fragments.append(_comparison("version", "<", criteria.last_version))
    if criteria.provider is not None:
        fragments.append(_comparison("provider", "=", criteria.provider))
    if criteria.text is not None and len(criteria.text) > 0:
        fragments.append(_text_search_condition("name", criteria.text))
    duration_fragment = _build_duration_condition("duration", criteria.min_duration, criteria.max_duration)
    if duration_fragment is not None:
        fragments.append(duration_fragment)
    return fragments


def _build_duration_condition(
        column: str, min_duration: int | None, max_duration: int | None,
) -> SqlFragment | None:
    if min_duration is not None and max_duration is not None:
        return SqlFragment(f"{column} BETWEEN %s AND %s", (min_duration, max_duration))
    if max_duration is not None:
        return SqlFragment(f"({column} IS NULL OR {column} <= %s)", (max_duration,))
    if min_duration is not None:
        return SqlFragment(f"({column} IS NULL OR {column} >= %s)", (min_duration,))
    return None


def _build_interaction_condition(criteria: ItemFilterCriteria) -> SqlFragment | None:
    if criteria.interactions_from_user is None:
        return None
    user_id = criteria.interactions_from_user
    or_fragments: list[SqlFragment] = []
    if criteria.interactions.without_interactions:
        or_fragments.append(SqlFragment(
            "NOT EXISTS (SELECT 1 FROM interactions ix WHERE ix.item_uuid = items.uuid "
            "AND ix.user_uuid = %s)",
            (user_id,),
        ))
    for flag, interaction_type in (
        (criteria.interactions.recommended, InteractionType.RECOMMENDED),
        (criteria.interactions.discouraged, InteractionType.DISCOURAGED),
        (criteria.interactions.viewed, InteractionType.VIEWED),
        (criteria.interactions.hidden, InteractionType.HIDDEN),
    ):
        if flag:
            or_fragments.append(SqlFragment(
                "EXISTS (SELECT 1 FROM interactions ix WHERE ix.item_uuid = items.uuid "
                "AND ix.user_uuid = %s AND ix.type = %s)",
                (user_id, interaction_type.value),
            ))
    if not or_fragments:
        return SqlFragment("FALSE")
    joined = _join(or_fragments, " OR ")
    return SqlFragment(f"({joined.placeholders})", joined.params)


class PostgresItemRepository(ItemRepository):
    def __init__(self, ip: IPv4Address, port: int, db_name: str, username: str, password: str) -> None:
        super().__init__()
        self._connector = PostgresConnector(ip, port, db_name, username, password)

    async def analyze(self) -> None:
        """
        Refresh planner statistics for items/interactions.

        A freshly bulk-loaded table has no statistics until autovacuum's autoanalyze gets to
        it, which can take well over a minute - without stats the planner badly misjudges the
        interaction EXISTS subqueries in find_items (nested-loop instead of hash join).
        """
        pool = await self._connector.pool()
        await pool.execute("ANALYZE items")
        await pool.execute("ANALYZE interactions")

    async def upsert_items(self, items: list[Item]) -> None:
        if len(items) == 0:
            return
        pool = await self._connector.pool()
        await pool.executemany(
            """
            INSERT INTO items (
                uuid, subscription_uuid, name, description, url, thumbnail,
                created_at, updated_at, published_at, provider, deleted_at, duration, version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (uuid) DO UPDATE SET
                subscription_uuid = EXCLUDED.subscription_uuid,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                url = EXCLUDED.url,
                thumbnail = EXCLUDED.thumbnail,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                published_at = EXCLUDED.published_at,
                provider = EXCLUDED.provider,
                deleted_at = EXCLUDED.deleted_at,
                duration = EXCLUDED.duration,
                version = EXCLUDED.version
            """,
            [
                (
                    item.uuid, item.subscription_uuid, item.name, item.description,
                    str(item.url), str(item.thumbnail), item.created_at, item.updated_at,
                    item.published_at, item.provider, item.deleted_at, item.duration, item.version,
                )
                for item in items
            ],
        )

    async def get_item(self, item_id: UUID) -> Item | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM items WHERE uuid = %s", item_id)
        if row is None or row["deleted_at"] is not None:
            return None
        return _row_to_item(row)

    async def delete_item(self, item_id: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute(
            "UPDATE items SET deleted_at = %s WHERE uuid = %s", datetime.now(timezone.utc), item_id,
        )

    async def find_items(self, criteria: ItemFilterCriteria, page_number: int, limit: int) -> list[Item]:
        pool = await self._connector.pool()
        fragments = _build_item_conditions(criteria)
        interaction_fragment = _build_interaction_condition(criteria)
        if interaction_fragment is not None:
            fragments = [*fragments, interaction_fragment]

        where_clause = _join(fragments, " AND ")
        query = (
            "SELECT * FROM items WHERE " + where_clause.placeholders  # noqa: S608
            + " ORDER BY published_at DESC LIMIT %s OFFSET %s"
        )
        params = (*where_clause.params, limit, page_number * limit)
        rows = await pool.fetch(query, *params)
        return [_row_to_item(row) for row in rows]

    async def delete_all_items(self) -> None:
        pool = await self._connector.pool()
        await pool.execute("UPDATE items SET deleted_at = %s", datetime.now(timezone.utc))

    async def add_interaction(self, interaction: Interaction) -> None:
        pool = await self._connector.pool()
        await pool.execute(
            "INSERT INTO interactions (uuid, item_uuid, user_uuid, type, created_at) VALUES (%s, %s, %s, %s, %s)",
            interaction.uuid, interaction.item_uuid, interaction.user_uuid,
            interaction.type.value, interaction.created_at,
        )

    async def get_interaction(self, interaction_id: UUID) -> Interaction | None:
        pool = await self._connector.pool()
        row = await pool.fetchrow("SELECT * FROM interactions WHERE uuid = %s", interaction_id)
        return None if row is None else _row_to_interaction(row)

    async def delete_interaction(self, interaction_id: UUID) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM interactions WHERE uuid = %s", interaction_id)

    async def delete_all_interactions(self) -> None:
        pool = await self._connector.pool()
        await pool.execute("DELETE FROM interactions")

    async def get_user_interactions_by_item_id(
            self, user_id: UUID, item_ids: list[UUID],
    ) -> dict[UUID, list[Interaction]]:
        pool = await self._connector.pool()
        rows = await pool.fetch(
            "SELECT * FROM interactions WHERE user_uuid = %s AND item_uuid = ANY(%s::uuid[])",
            user_id, item_ids,
        )
        result: dict[UUID, list[Interaction]] = {item_id: [] for item_id in item_ids}
        for row in rows:
            result[row["item_uuid"]].append(_row_to_interaction(row))
        return result

    async def find_interactions(
            self, criteria: InteractionFilterCriteria, page_number: int, limit: int,
    ) -> list[Interaction]:
        pool = await self._connector.pool()
        fragments: list[SqlFragment] = []
        if criteria.item_ids is not None:
            fragments.append(_uuid_array_condition("i.item_uuid", list(criteria.item_ids)))
        if criteria.user_ids is not None:
            fragments.append(_uuid_array_condition("i.user_uuid", list(criteria.user_ids)))
        if criteria.interaction_types is not None:
            types = [interaction_type.value for interaction_type in criteria.interaction_types]
            fragments.append(SqlFragment("i.type = ANY(%s::text[])", (types,)))
        if criteria.created_before is not None:
            fragments.append(_comparison("i.created_at", "<", criteria.created_before))

        join_clause = ""
        if any(value is not None for value in (criteria.text, criteria.min_duration, criteria.max_duration)):
            join_clause = "JOIN items it ON it.uuid = i.item_uuid"
            fragments.append(SqlFragment("it.deleted_at IS NULL"))
            if criteria.text is not None and len(criteria.text) > 0:
                fragments.append(_text_search_condition("it.name", criteria.text))
            duration_fragment = _build_duration_condition("it.duration", criteria.min_duration, criteria.max_duration)
            if duration_fragment is not None:
                fragments.append(duration_fragment)

        where = _join(fragments, " AND ")
        where_clause = f" WHERE {where.placeholders}" if fragments else ""
        query = (
            f"SELECT i.* FROM interactions i {join_clause}{where_clause} "  # noqa: S608
            "ORDER BY i.created_at DESC LIMIT %s OFFSET %s"
        )
        params = (*where.params, limit, page_number * limit)
        rows = await pool.fetch(query, *params)
        return [_row_to_interaction(row) for row in rows]

    async def count_items(self, provider: ItemProvider | None = None) -> int:
        pool = await self._connector.pool()
        if provider is None:
            return await pool.fetchval("SELECT COUNT(*) FROM items WHERE deleted_at IS NULL")
        return await pool.fetchval(
            "SELECT COUNT(*) FROM items WHERE deleted_at IS NULL AND provider = %s", provider,
        )
