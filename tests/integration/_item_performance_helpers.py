"""
Scenario definitions and data generators shared by the find_items performance tests.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable
from uuid import UUID, uuid4

from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import AnyItemInteraction, ItemFilterCriteria, ItemRepository


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


def default_find_queries(user_uuid: UUID, subscription_ids: list[UUID]) -> list[FindItemsQueryCase]:
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
            max_baseline_multiplier=3.0,
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


def build_standard_scenarios(user_uuid: UUID) -> list[FindItemsPerformanceTestScenario]:
    """The three catalogue-growth scenarios exercised by test_find_items_performance."""
    subscription_ids = [uuid4()]
    return [
        FindItemsPerformanceTestScenario(
            name="10K items, 0 interactions",
            total_items=10000,
            subscription_ids=subscription_ids,
            items_with_interactions=0,
            total_interactions=0,
            queries=default_find_queries(user_uuid, subscription_ids),
        ),
        FindItemsPerformanceTestScenario(
            name="10K items, 10K interactions",
            total_items=10000,
            subscription_ids=subscription_ids,
            items_with_interactions=10000,
            total_interactions=10000,
            queries=default_find_queries(user_uuid, subscription_ids),
        ),
        FindItemsPerformanceTestScenario(
            name="7.5K items without interactions + 2.5K items with 10K interactions",
            total_items=10000,
            subscription_ids=subscription_ids,
            items_with_interactions=2500,
            total_interactions=10000,
            queries=default_find_queries(user_uuid, subscription_ids),
        ),
    ]


def build_duration_filter_scenario(user_uuid: UUID) -> FindItemsPerformanceTestScenario:
    """The duration-filter scenario exercised by test_find_items_duration_filter_performance."""
    # Spread items over a pool of subscriptions; queries filter by a followed subset, like the
    # followed-subscriptions / topic listings do.
    subscription_ids = [uuid4() for _ in range(50)]
    followed_subscription_ids = subscription_ids[:10]

    return FindItemsPerformanceTestScenario(
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


async def run_find_items_scenario(
        repo: ItemRepository,
        scenario: FindItemsPerformanceTestScenario,
        user_uuid: UUID,
        baseline_time: float,
        limit: int = 100,
        after_insert: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """
    Set up a scenario's data and measure each of its find_items queries.

    `after_insert`, if given, runs once the data is loaded and before any query is measured -
    Postgres uses this to ANALYZE the tables, since a freshly bulk-loaded table has no planner
    statistics yet and autovacuum's autoanalyze won't have run within a test's lifetime.
    """
    logging.info(f"=== Testing scenario: {scenario.name} ===")

    await repo.delete_all_items()
    await repo.delete_all_interactions()

    logging.info("Generating test data...")
    start_time = time.time()
    items = await generate_items(scenario.total_items, scenario.subscription_ids)
    interactions = await generate_interactions(
        items[: scenario.items_with_interactions],
        user_uuid,
        scenario.total_interactions,
    )
    logging.info(f"Data generation completed in {time.time() - start_time:.3f}s")

    logging.info("Inserting items...")
    start_time = time.time()
    await insert_items_in_batches(repo, items, batch_size=10_000)
    logging.info(f"Items inserted in {time.time() - start_time:.3f}s")

    logging.info("Inserting interactions...")
    start_time = time.time()
    await insert_interactions_in_batches(repo, interactions, batch_size=10_000)
    logging.info(f"Interactions inserted in {time.time() - start_time:.3f}s")

    if after_insert is not None:
        start_time = time.time()
        await after_insert()
        logging.info(f"Post-insert hook completed in {time.time() - start_time:.3f}s")

    for query in scenario.queries:
        await measure_find_items_query(
            repo=repo,
            query=query,
            limit=limit,
            max_expected_time=baseline_time * query.max_baseline_multiplier,
        )


async def measure_find_items_query(
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


async def generate_items(count: int, subscription_ids: list[UUID]) -> list[Item]:
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


async def generate_interactions(items: list[Item], user_uuid: UUID, count: int) -> list[Interaction]:
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


async def insert_items_in_batches(repo: ItemRepository, items: list[Item], batch_size: int) -> None:
    """Insert items in batches to avoid memory issues"""
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        await repo.upsert_items(batch)

        if (i // batch_size + 1) % 10 == 0:  # Progress indicator every 10 batches
            logging.info(f"  Inserted {min(i + batch_size, len(items)):,} / {len(items):,} items")


async def insert_interactions_in_batches(
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


def baseline_function() -> int:
    """
    A simple function to establish a baseline for performance.

    It takes around 60ms to execute on a 3.8GHz CPU.
    """
    total = 0
    for i in range(1000000):
        total += i
    return total
