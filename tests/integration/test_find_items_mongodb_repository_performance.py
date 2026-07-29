import logging
import time
from ipaddress import IPv4Address
from uuid import uuid4

import pytest

from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository
from tests.integration._item_performance_helpers import (
    baseline_function,
    build_duration_filter_scenario,
    build_standard_scenarios,
    run_find_items_scenario,
)


@pytest.fixture(name="mongodb_item_repo", scope="session")
def fixture_mongodb_item_repo(db_name: str) -> ItemRepository:
    return MongoDBItemRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


@pytest.fixture(name="baseline_time", scope="session")
def fixture_baseline_time() -> float:
    """Establish a per-machine performance baseline (measured once) used to scale the assertions."""
    start_time = time.time()
    baseline_function()
    baseline_time = time.time() - start_time
    logging.info(f"Baseline function executed in {baseline_time:.3f}s")
    return baseline_time


@pytest.mark.asyncio()
async def test_find_items_performance(mongodb_item_repo: ItemRepository, baseline_time: float) -> None:
    """
    Measure that listing a user's items stays fast as their interaction history grows.

    Covers the typical feed views a user requests -- items they have not interacted with yet,
    items they have already viewed, and the full list of items -- across catalogues ranging
    from no interactions at all to one interaction on every item.
    """
    user_uuid = uuid4()

    for scenario in build_standard_scenarios(user_uuid):
        await run_find_items_scenario(mongodb_item_repo, scenario, user_uuid, baseline_time)


@pytest.mark.asyncio()
async def test_find_items_duration_filter_performance(mongodb_item_repo: ItemRepository, baseline_time: float) -> None:
    """
    Measure that listing a user's items stays fast when filtering by video duration.

    Covers filtering by a minimum duration, a maximum duration, and a duration range, both on
    their own and combined with the user's viewed history, to ensure duration filters remain
    fast on a large catalogue spread across many subscriptions.
    """
    user_uuid = uuid4()
    scenario = build_duration_filter_scenario(user_uuid)
    await run_find_items_scenario(mongodb_item_repo, scenario, user_uuid, baseline_time)
