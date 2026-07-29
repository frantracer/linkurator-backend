import logging
import time
from ipaddress import IPv4Address
from uuid import uuid4

import pytest

from linkurator_core.infrastructure.postgres.item_repository import PostgresItemRepository
from tests.integration._item_performance_helpers import (
    baseline_function,
    build_duration_filter_scenario,
    build_standard_scenarios,
    run_find_items_scenario,
)


@pytest.fixture(name="postgres_item_repo", scope="session")
def fixture_postgres_item_repo(db_name: str) -> PostgresItemRepository:
    return PostgresItemRepository(IPv4Address("127.0.0.1"), 5432, db_name, "develop", "develop")


@pytest.fixture(name="baseline_time", scope="session")
def fixture_baseline_time() -> float:
    """Establish a per-machine performance baseline (measured once) used to scale the assertions."""
    start_time = time.time()
    baseline_function()
    baseline_time = time.time() - start_time
    logging.info(f"Baseline function executed in {baseline_time:.3f}s")
    return baseline_time


@pytest.mark.asyncio()
async def test_find_items_performance(postgres_item_repo: PostgresItemRepository, baseline_time: float) -> None:
    """
    Measure that listing a user's items stays fast as their interaction history grows.

    Same scenarios as the MongoDB counterpart (see _item_performance_helpers.py) so the two
    backends are held to the same data and thresholds. ANALYZE runs after seeding each
    scenario: a freshly loaded table has no planner statistics yet, and autovacuum's
    autoanalyze won't have run within a test's lifetime (its naptime defaults to 60s), so
    without an explicit ANALYZE this test would consistently hit a cold, unrepresentative
    query plan rather than the steady-state one Postgres runs in production.
    """
    user_uuid = uuid4()

    for scenario in build_standard_scenarios(user_uuid):
        await run_find_items_scenario(
            postgres_item_repo, scenario, user_uuid, baseline_time,
            after_insert=postgres_item_repo.analyze,
        )


@pytest.mark.asyncio()
async def test_find_items_duration_filter_performance(
        postgres_item_repo: PostgresItemRepository, baseline_time: float,
) -> None:
    """Measure that listing a user's items stays fast when filtering by video duration."""
    user_uuid = uuid4()
    scenario = build_duration_filter_scenario(user_uuid)
    await run_find_items_scenario(
        postgres_item_repo, scenario, user_uuid, baseline_time,
        after_insert=postgres_item_repo.analyze,
    )
