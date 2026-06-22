import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address
from uuid import UUID, uuid4

import pytest

from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import (
    AnyItemInteraction,
    ItemFilterCriteria,
    ItemRepository,
)
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository


@dataclass
class FindItemsQueryCase:
    name: str
    criteria: ItemFilterCriteria
    check_items_result: bool
    max_baseline_multiplier: float


@dataclass
class FindItemsPerformanceTestScenario:
    name: str
    total_items: int
    subscription_ids: list[UUID]
    items_with_interactions: int
    total_interactions: int
    queries: list[FindItemsQueryCase]


def _default_find_queries(user_uuid: UUID, subscription_ids: list[UUID]) -> list[FindItemsQueryCase]:
    """The find_items queries (all filtering by subscription_ids) exercised against each scenario."""
    return [
        FindItemsQueryCase(
            name="without_interactions",
            criteria=ItemFilterCriteria(
                subscription_ids=subscription_ids,
                interactions=AnyItemInteraction(without_interactions=True),
                interactions_from_user=user_uuid,
            ),
            check_items_result=False,
            max_baseline_multiplier=15.0,
        ),
        FindItemsQueryCase(
            name="viewed_items",
            criteria=ItemFilterCriteria(
                subscription_ids=subscription_ids,
                interactions=AnyItemInteraction(viewed=True),
                interactions_from_user=user_uuid,
            ),
            check_items_result=False,
            max_baseline_multiplier=3.0,
        ),
        FindItemsQueryCase(
            name="any_items",
            criteria=ItemFilterCriteria(subscription_ids=subscription_ids),
            check_items_result=True,
            max_baseline_multiplier=1.5,
        ),
    ]


@pytest.fixture(name="mongodb_item_repo", scope="session")
def fixture_mongodb_item_repo(db_name: str) -> ItemRepository:
    return MongoDBItemRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


@pytest.fixture(name="baseline_time", scope="session")
def fixture_baseline_time() -> float:
    """Establish a per-machine performance baseline (measured once) used to scale the assertions."""
    start_time = time.time()
    _baseline_function()
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
    subscription_ids = [uuid4()]

    scenarios: list[FindItemsPerformanceTestScenario] = [
        FindItemsPerformanceTestScenario(
            name="10K items, 0 interactions",
            total_items=10000,
            subscription_ids=subscription_ids,
            items_with_interactions=0,
            total_interactions=0,
            queries=_default_find_queries(user_uuid, subscription_ids),
        ),
        FindItemsPerformanceTestScenario(
            name="10K items, 10K interactions",
            total_items=10000,
            subscription_ids=subscription_ids,
            items_with_interactions=10000,
            total_interactions=10000,
            queries=_default_find_queries(user_uuid, subscription_ids),
        ),
        FindItemsPerformanceTestScenario(
            name="7.5K items without interactions + 2.5K items with 10K interactions",
            total_items=10000,
            subscription_ids=subscription_ids,
            items_with_interactions=2500,
            total_interactions=10000,
            queries=_default_find_queries(user_uuid, subscription_ids),
        ),
    ]

    for scenario in scenarios:
        await _test_find_items_scenario(mongodb_item_repo, scenario, user_uuid, baseline_time)


@pytest.mark.asyncio()
async def test_find_items_duration_filter_performance(mongodb_item_repo: ItemRepository, baseline_time: float) -> None:
    """
    Measure that listing a user's items stays fast when filtering by video duration.

    Covers filtering by a minimum duration, a maximum duration, and a duration range, both on
    their own and combined with the user's viewed history, to ensure duration filters remain
    fast on a large catalogue spread across many subscriptions.
    """
    user_uuid = uuid4()

    # Spread items over a pool of subscriptions; queries filter by a followed subset, like the
    # followed-subscriptions / topic listings do.
    subscription_ids = [uuid4() for _ in range(50)]
    followed_subscription_ids = subscription_ids[:10]

    # Durations are spread over 0..7199 seconds (see _generate_items), so a 600..1800s window
    # selects a middle slice of the catalogue.
    scenario = FindItemsPerformanceTestScenario(
        name="10K items over 50 subscriptions, every item with an interaction",
        total_items=10000,
        subscription_ids=subscription_ids,
        items_with_interactions=10000,
        total_interactions=10000,
        queries=[
            FindItemsQueryCase(
                name="duration range (min+max)",
                criteria=ItemFilterCriteria(
                    subscription_ids=followed_subscription_ids,
                    min_duration=600,
                    max_duration=1800,
                ),
                check_items_result=False,
                max_baseline_multiplier=3.0,
            ),
            FindItemsQueryCase(
                name="max duration only (or-null wildcard)",
                criteria=ItemFilterCriteria(
                    subscription_ids=followed_subscription_ids,
                    max_duration=1800,
                ),
                check_items_result=False,
                max_baseline_multiplier=3.0,
            ),
            FindItemsQueryCase(
                name="min duration only (or-null wildcard)",
                criteria=ItemFilterCriteria(
                    subscription_ids=followed_subscription_ids,
                    min_duration=1800,
                ),
                check_items_result=False,
                max_baseline_multiplier=3.0,
            ),
            FindItemsQueryCase(
                name="duration range + viewed interactions (right-join path)",
                criteria=ItemFilterCriteria(
                    subscription_ids=followed_subscription_ids,
                    min_duration=600,
                    max_duration=1800,
                    interactions=AnyItemInteraction(viewed=True),
                    interactions_from_user=user_uuid,
                ),
                check_items_result=False,
                max_baseline_multiplier=4.0,
            ),
        ],
    )

    await _test_find_items_scenario(mongodb_item_repo, scenario, user_uuid, baseline_time)


async def _test_find_items_scenario(
    repo: ItemRepository,
    scenario: FindItemsPerformanceTestScenario,
    user_uuid: UUID,
    baseline_time: float,
    limit: int = 100,
) -> None:
    """Set up a scenario's data and measure each of its find_items queries."""
    logging.info(f"=== Testing scenario: {scenario.name} ===")

    await repo.delete_all_items()
    await repo.delete_all_interactions()

    logging.info("Generating test data...")
    start_time = time.time()
    items = await _generate_items(scenario.total_items, scenario.subscription_ids)
    interactions = await _generate_interactions(
        items[: scenario.items_with_interactions],
        user_uuid,
        scenario.total_interactions,
    )
    logging.info(f"Data generation completed in {time.time() - start_time:.3f}s")

    logging.info("Inserting items...")
    start_time = time.time()
    await _insert_items_in_batches(repo, items, batch_size=10_000)
    logging.info(f"Items inserted in {time.time() - start_time:.3f}s")

    logging.info("Inserting interactions...")
    start_time = time.time()
    await _insert_interactions_in_batches(repo, interactions, batch_size=10_000)
    logging.info(f"Interactions inserted in {time.time() - start_time:.3f}s")

    for query in scenario.queries:
        await _measure_find_items_query(
            repo=repo,
            query=query,
            limit=limit,
            max_expected_time=baseline_time * query.max_baseline_multiplier,
        )


async def _measure_find_items_query(
    repo: ItemRepository,
    query: FindItemsQueryCase,
    limit: int,
    max_expected_time: float,
) -> None:
    """Run a single find_items query several times and assert its average latency."""
    logging.info(f"Find {limit} {query.name}")

    # Warmup run
    await repo.find_items(query.criteria, 0, limit)

    # Performance test - run 3 times and take average
    times = []
    for run in range(3):
        start_time = time.time()
        results = await repo.find_items(query.criteria, 0, limit)
        execution_time = time.time() - start_time
        times.append(execution_time)

        logging.info(f"  Run {run + 1}: Found {len(results)} items in {execution_time:.3f}s")

        # Verify we got some results for scenarios that should return data
        if query.check_items_result:
            assert len(results) > 0, f"Expected results for {query.name} but got none"

    avg_time = sum(times) / len(times)
    logging.info(f"  Average time for {query.name}: {avg_time:.3f}s, max expected {max_expected_time:.3f}s")

    assert avg_time < max_expected_time, (
        f"Average time for {query.name} ({avg_time:.3f}s) exceeded baseline ({max_expected_time:.3f}s)"
    )


async def _generate_items(count: int, subscription_ids: list[UUID]) -> list[Item]:
    """
    Generate items with distinct published_at timestamps and varied durations.

    Durations cycle through 0..7199 seconds; every 10th item has `None` duration.
    """
    items = []
    base_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(count):
        duration = None if i % 10 == 0 else (i * 7) % 7200
        item = mock_item(
            item_uuid=uuid4(),
            sub_uuid=subscription_ids[i % len(subscription_ids)],
            name=f"Test Item {i}",
            description=f"Description for item {i}",
            published_at=base_date + timedelta(minutes=i),
            created_at=base_date,
            updated_at=base_date,
            duration=duration,
            provider="youtube",
        )
        items.append(item)

    return items


async def _generate_interactions(items: list[Item], user_uuid: UUID, count: int) -> list[Interaction]:
    """Generate test interactions"""
    if not items or count == 0:
        return []

    interactions = []
    interaction_types = [
        InteractionType.VIEWED,
        InteractionType.RECOMMENDED,
        InteractionType.DISCOURAGED,
        InteractionType.HIDDEN,
    ]

    for i in range(count):
        item = items[i % len(items)]
        interaction_type = interaction_types[i % len(interaction_types)]

        interaction = Interaction(
            uuid=uuid4(),
            item_uuid=item.uuid,
            user_uuid=user_uuid,
            type=interaction_type,
            created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        interactions.append(interaction)

    return interactions


async def _insert_items_in_batches(repo: ItemRepository, items: list[Item], batch_size: int) -> None:
    """Insert items in batches to avoid memory issues"""
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        await repo.upsert_items(batch)

        if (i // batch_size + 1) % 10 == 0:  # Progress indicator every 10 batches
            logging.info(f"  Inserted {min(i + batch_size, len(items)):,} / {len(items):,} items")


async def _insert_interactions_in_batches(
    repo: ItemRepository, interactions: list[Interaction], batch_size: int,
) -> None:
    """Insert interactions in batches"""
    for i in range(0, len(interactions), batch_size):
        batch = interactions[i : i + batch_size]

        # Insert interactions one by one as the repository doesn't support batch insert
        tasks = []
        for interaction in batch:
            tasks.append(repo.add_interaction(interaction))

        await asyncio.gather(*tasks)

        if (i // batch_size + 1) % 10 == 0:  # Progress indicator every 10 batches
            logging.info(f"  Inserted {min(i + batch_size, len(interactions)):,} / {len(interactions):,} interactions")


def _baseline_function() -> int:
    """
    A simple function to establish a baseline for performance.

    It takes around 60ms to execute on a 3.8GHz CPU.
    """
    total = 0
    for i in range(1000000):
        total += i
    return total
