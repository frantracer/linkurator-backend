"""
One-shot ETL: copies every MongoDB collection into the PostgreSQL schema.

Usage:
    PYTHONPATH='.' .venv/bin/python3 scripts/migrate_mongo_to_postgres.py [--only TABLE ...] [--verify-only]

Runs the Postgres schema migrations first (safe/idempotent, pass --skip-schema-setup to skip
this). Each target table is then TRUNCATEd before it is reloaded, so the whole script is safe
to re-run repeatedly during a rehearsal - it is a full resync, not an incremental sync.

`sessions` is intentionally NOT migrated: sessions are short-lived and users simply log in
again after cutover, so there is nothing worth preserving there.

`items` and `interactions` are the tables expected to hold the bulk of the data, so they are
loaded via raw COPY instead of the repository's row-at-a-time methods.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient

from linkurator_core.infrastructure.config.settings import ApplicationSettings, MongoDBSettings, PostgresSettings
from linkurator_core.infrastructure.mongodb.chat_repository import MongoDBChat
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBInteraction, MongoDBItem
from linkurator_core.infrastructure.mongodb.password_change_request_repository import MongoDBPasswordChangeRequest
from linkurator_core.infrastructure.mongodb.registration_request_repository import MongoDBRegistrationRequest
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscription
from linkurator_core.infrastructure.mongodb.topic_repository import MongoDBTopic
from linkurator_core.infrastructure.mongodb.user_filter_repository import MongoDBUserFilter
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUser
from linkurator_core.infrastructure.postgres.chat_repository import PostgresChatRepository
from linkurator_core.infrastructure.postgres.common import PostgresConnector
from linkurator_core.infrastructure.postgres.password_change_request_repository import (
    PostgresPasswordChangeRequestRepository,
)
from linkurator_core.infrastructure.postgres.registration_request_repository import (
    PostgresRegistrationRequestRepository,
)
from linkurator_core.infrastructure.postgres.repositories import run_postgres_migrations
from linkurator_core.infrastructure.postgres.rss_data_repository import PostgresRssDataRepository
from linkurator_core.infrastructure.postgres.subscription_repository import PostgresSubscriptionRepository
from linkurator_core.infrastructure.postgres.topic_repository import PostgresTopicRepository
from linkurator_core.infrastructure.postgres.user_filter_repository import PostgresUserFilterRepository
from linkurator_core.infrastructure.postgres.user_repository import (
    INSERT_COLUMNS as USER_INSERT_COLUMNS,
)
from linkurator_core.infrastructure.postgres.user_repository import (
    INSERT_PLACEHOLDERS as USER_INSERT_PLACEHOLDERS,
)
from linkurator_core.infrastructure.postgres.user_repository import PostgresUserRepository, user_params
from linkurator_core.infrastructure.rss.rss_data_repository import RawDataRecord

logging.basicConfig(format="%(asctime)s - %(levelname)s: %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("migrate_mongo_to_postgres")

BATCH_SIZE = 2000

ITEM_COLUMNS = [
    "uuid", "subscription_uuid", "name", "description", "url", "thumbnail",
    "created_at", "updated_at", "published_at", "provider", "deleted_at", "duration", "version",
]
INTERACTION_COLUMNS = ["uuid", "item_uuid", "user_uuid", "type", "created_at"]

# Order is a readability/safety convention, not DB-enforced: no foreign keys exist between
# these tables (Mongo has none either), so any subset can be migrated independently via --only.
MIGRATION_ORDER = [
    "users", "deleted_users", "subscriptions", "topics", "chats", "user_filters",
    "rss_data", "registration_requests", "password_change_requests",
    "items", "interactions",
]


@dataclass
class MigrationContext:
    mongo_settings: MongoDBSettings
    postgres_settings: PostgresSettings
    mongo_client: AsyncIOMotorClient[Any]
    postgres_connector: PostgresConnector

    def mongo_collection(self, name: str) -> Any:
        codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)  # type: ignore
        return self.mongo_client.get_database(
            self.mongo_settings.database, codec_options=codec_options,
        ).get_collection(name)


async def _truncate(ctx: MigrationContext, table_name: str) -> None:
    pool = await ctx.postgres_connector.pool()
    await pool.execute(f"TRUNCATE TABLE {table_name} CASCADE")  # -- table_name is an internal constant


# Tables with a child table that also gets bulk-loaded and needs its own fresh statistics.
CHILD_TABLES = {"chats": ["chat_messages"]}


async def _analyze(ctx: MigrationContext, table_name: str) -> None:
    """
    Refresh planner statistics after a bulk load.

    A freshly COPY/INSERT-loaded table has no statistics until autovacuum's autoanalyze gets
    around to it, which can take a while and won't have run before the first post-cutover
    queries. Without stats the planner badly misjudges selectivity on the interaction EXISTS
    subqueries in find_items - a nested-loop plan that should take ~3ms takes ~2s instead.
    """
    pool = await ctx.postgres_connector.pool()
    for table in [table_name, *CHILD_TABLES.get(table_name, [])]:
        await pool.execute(f"ANALYZE {table}")  # -- table is an internal constant


async def migrate_users(ctx: MigrationContext) -> int:
    await _truncate(ctx, "users")
    repo = PostgresUserRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    async for doc in ctx.mongo_collection("users").find({}, batch_size=BATCH_SIZE):
        await repo.add(MongoDBUser(**doc).to_domain_user())
        count += 1
    return count


async def migrate_deleted_users(ctx: MigrationContext) -> int:
    """
    Copy the soft-delete archive MongoDBUserRepository.delete() writes to on every deletion.

    Nothing in the app reads this back today, but it's real historical data (an account
    deletion audit trail), not derived/regenerable state, so it gets migrated like anything
    else rather than silently dropped.
    """
    await _truncate(ctx, "deleted_users")
    pool = await ctx.postgres_connector.pool()
    count = 0
    async for doc in ctx.mongo_collection("deleted_users").find({}, batch_size=BATCH_SIZE):
        user = MongoDBUser(**doc).to_domain_user()
        await pool.execute(
            f"INSERT INTO deleted_users ({USER_INSERT_COLUMNS}, deleted_at) "  # noqa: S608
            f"VALUES ({USER_INSERT_PLACEHOLDERS}, %s)",
            *user_params(user), doc["deleted_at"],
        )
        count += 1
    return count


async def migrate_subscriptions(ctx: MigrationContext) -> int:
    await _truncate(ctx, "subscriptions")
    repo = PostgresSubscriptionRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    async for doc in ctx.mongo_collection("subscriptions").find({}, batch_size=BATCH_SIZE):
        await repo.add(MongoDBSubscription(**doc).to_domain_subscription())
        count += 1
    return count


async def migrate_topics(ctx: MigrationContext) -> int:
    await _truncate(ctx, "topics")
    repo = PostgresTopicRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    async for doc in ctx.mongo_collection("topics").find({}, batch_size=BATCH_SIZE):
        await repo.add(MongoDBTopic(**doc).to_domain_topic())
        count += 1
    return count


async def migrate_chats(ctx: MigrationContext) -> int:
    await _truncate(ctx, "chats")
    repo = PostgresChatRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    async for doc in ctx.mongo_collection("chats").find({}, batch_size=BATCH_SIZE):
        await repo.add(MongoDBChat(**doc).to_domain_chat())
        count += 1
    return count


async def migrate_user_filters(ctx: MigrationContext) -> int:
    await _truncate(ctx, "user_filters")
    repo = PostgresUserFilterRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    async for doc in ctx.mongo_collection("user_filters").find({}, batch_size=BATCH_SIZE):
        await repo.upsert(MongoDBUserFilter(**doc).to_domain())
        count += 1
    return count


async def migrate_rss_data(ctx: MigrationContext) -> int:
    await _truncate(ctx, "rss_data")
    repo = PostgresRssDataRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    batch: list[RawDataRecord] = []
    async for doc in ctx.mongo_collection("rss_data").find({}, batch_size=BATCH_SIZE):
        batch.append(RawDataRecord(rss_url=doc["rss_url"], item_url=doc["item_url"], raw_data=doc["raw_data"]))
        if len(batch) >= BATCH_SIZE:
            await repo.set_raw_data(batch)
            count += len(batch)
            batch = []
    if batch:
        await repo.set_raw_data(batch)
        count += len(batch)
    return count


async def migrate_registration_requests(ctx: MigrationContext) -> int:
    await _truncate(ctx, "registration_requests")
    repo = PostgresRegistrationRequestRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    async for doc in ctx.mongo_collection("registration_requests").find({}, batch_size=BATCH_SIZE):
        await repo.add_request(MongoDBRegistrationRequest(**doc).to_domain_registration_request())
        count += 1
    return count


async def migrate_password_change_requests(ctx: MigrationContext) -> int:
    await _truncate(ctx, "password_change_requests")
    repo = PostgresPasswordChangeRequestRepository(
        ctx.postgres_settings.ip_address, ctx.postgres_settings.port,
        ctx.postgres_settings.database, ctx.postgres_settings.user, ctx.postgres_settings.password,
    )
    count = 0
    async for doc in ctx.mongo_collection("password_change_requests").find({}, batch_size=BATCH_SIZE):
        await repo.add_request(MongoDBPasswordChangeRequest(**doc).to_domain_password_change_request())
        count += 1
    return count


async def migrate_items(ctx: MigrationContext) -> int:
    await _truncate(ctx, "items")
    pool = await ctx.postgres_connector.pool()
    count = 0
    async with pool.acquire() as conn:
        batch: list[tuple[Any, ...]] = []
        async for doc in ctx.mongo_collection("items").find({}, batch_size=BATCH_SIZE):
            item = MongoDBItem(**doc).to_domain_item()
            batch.append((
                item.uuid, item.subscription_uuid, item.name, item.description,
                str(item.url), str(item.thumbnail), item.created_at, item.updated_at,
                item.published_at, item.provider, item.deleted_at, item.duration, item.version,
            ))
            if len(batch) >= BATCH_SIZE:
                await conn.copy_records_to_table("items", records=batch, columns=ITEM_COLUMNS)
                count += len(batch)
                batch = []
        if batch:
            await conn.copy_records_to_table("items", records=batch, columns=ITEM_COLUMNS)
            count += len(batch)
    return count


async def migrate_interactions(ctx: MigrationContext) -> int:
    await _truncate(ctx, "interactions")
    pool = await ctx.postgres_connector.pool()
    count = 0
    async with pool.acquire() as conn:
        batch: list[tuple[Any, ...]] = []
        async for doc in ctx.mongo_collection("interactions").find({}, batch_size=BATCH_SIZE):
            interaction = MongoDBInteraction(**doc).to_domain_interaction()
            batch.append((
                interaction.uuid, interaction.item_uuid, interaction.user_uuid,
                interaction.type.value, interaction.created_at,
            ))
            if len(batch) >= BATCH_SIZE:
                await conn.copy_records_to_table("interactions", records=batch, columns=INTERACTION_COLUMNS)
                count += len(batch)
                batch = []
        if batch:
            await conn.copy_records_to_table("interactions", records=batch, columns=INTERACTION_COLUMNS)
            count += len(batch)
    return count


MIGRATORS: dict[str, Callable[[MigrationContext], Awaitable[int]]] = {
    "users": migrate_users,
    "deleted_users": migrate_deleted_users,
    "subscriptions": migrate_subscriptions,
    "topics": migrate_topics,
    "chats": migrate_chats,
    "user_filters": migrate_user_filters,
    "rss_data": migrate_rss_data,
    "registration_requests": migrate_registration_requests,
    "password_change_requests": migrate_password_change_requests,
    "items": migrate_items,
    "interactions": migrate_interactions,
}


async def verify(ctx: MigrationContext, tables: list[str]) -> bool:
    all_ok = True
    pool = await ctx.postgres_connector.pool()
    for name in tables:
        mongo_count = await ctx.mongo_collection(name).count_documents({})
        postgres_count = await pool.fetchval(f"SELECT COUNT(*) FROM {name}")  # noqa: S608 -- name is an internal constant
        ok = mongo_count == postgres_count
        all_ok = all_ok and ok
        logger.info(
            "%-25s mongo=%-8d postgres=%-8d %s", name, mongo_count, postgres_count, "OK" if ok else "MISMATCH",
        )
    return all_ok


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", choices=MIGRATION_ORDER, help="Only migrate/verify these tables")
    parser.add_argument("--verify-only", action="store_true", help="Skip the copy, only compare row counts")
    parser.add_argument(
        "--skip-schema-setup", action="store_true",
        help="Skip running Postgres migrations before the transfer",
    )
    return parser.parse_args()


async def main(settings: ApplicationSettings, tables: list[str], verify_only: bool) -> None:
    mongo_client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(
        f"mongodb://{settings.mongodb.ip_address!s}:{settings.mongodb.port}/",
        username=settings.mongodb.user, password=settings.mongodb.password,
    )
    postgres_connector = PostgresConnector(
        settings.postgres.ip_address, settings.postgres.port,
        settings.postgres.database, settings.postgres.user, settings.postgres.password,
    )
    ctx = MigrationContext(
        mongo_settings=settings.mongodb, postgres_settings=settings.postgres,
        mongo_client=mongo_client, postgres_connector=postgres_connector,
    )

    if not verify_only:
        overall_start = time.monotonic()
        for table in tables:
            table_start = time.monotonic()
            copied = await MIGRATORS[table](ctx)
            await _analyze(ctx, table)
            logger.info("%-25s copied %d rows in %.1fs", table, copied, time.monotonic() - table_start)
        logger.info("Transfer complete in %.1fs", time.monotonic() - overall_start)

    logger.info("Verifying row counts...")
    ok = await verify(ctx, tables)
    if not ok:
        logger.error("Verification FAILED - row counts do not match. Do not cut over.")
        sys.exit(1)
    logger.info("Verification passed - all row counts match.")


if __name__ == "__main__":
    cli_args = _parse_args()
    app_settings = ApplicationSettings.from_file()

    if not cli_args.skip_schema_setup:
        logger.info("Running Postgres schema migrations...")
        run_postgres_migrations(
            app_settings.postgres.ip_address, app_settings.postgres.port,
            app_settings.postgres.database, app_settings.postgres.user, app_settings.postgres.password,
        )

    asyncio.run(main(app_settings, cli_args.only or MIGRATION_ORDER, cli_args.verify_only))
