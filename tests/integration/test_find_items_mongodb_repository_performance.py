import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import IPv4Address
from uuid import UUID, uuid4

import pytest

from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import (
    AnyItemInteraction,
    ItemFilterCriteria,
    ItemRepository,
)
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository


@dataclass
class FindItemsPerformanceTestScenario:
    name: str
    total_items: int
    items_with_interactions: int
    total_interactions: int


@pytest.fixture(name="mongodb_item_repo", scope="session")
def fixture_mongodb_item_repo(db_name: str) -> ItemRepository:
    return MongoDBItemRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio()
async def test_find_items_performance(mongodb_item_repo: ItemRepository) -> None:
    """Performance test for find_items with various scenarios"""
    # Clean database
    await mongodb_item_repo.delete_all_items()
    await mongodb_item_repo.delete_all_interactions()

    # Test scenarios
    scenarios: list[FindItemsPerformanceTestScenario] = [
        FindItemsPerformanceTestScenario(
            name="10K items, 0 interactions",
            total_items=10000,
            items_with_interactions=0,
            total_interactions=0,
        ),
        FindItemsPerformanceTestScenario(
            name="10K items, 10K interactions",
            total_items=10000,
            items_with_interactions=10000,
            total_interactions=10000,
        ),
        FindItemsPerformanceTestScenario(
            name="7.5K items without interactions + 2.5K items with 10K interactions",
            total_items=10000,
            items_with_interactions=2500,
            total_interactions=10000,
        ),
    ]

    user_uuid = uuid4()

    baseline_start_time = time.time()
    baseline_function()
    baseline_end_time = time.time()
    baseline_time = baseline_end_time - baseline_start_time
    logging.info(f"Baseline function executed in {baseline_time:.3f}s")

    for scenario in scenarios:
        logging.info(f"=== Testing scenario: {scenario.name} ===")

        # Clean database for each scenario
        await mongodb_item_repo.delete_all_items()
        await mongodb_item_repo.delete_all_interactions()

        # Generate test data
        logging.info("Generating test data...")
        start_time = time.time()

        items = await _generate_items(scenario.total_items)
        interactions = await _generate_interactions(
            items[:scenario.items_with_interactions],
            user_uuid,
            scenario.total_interactions,
        )

        logging.info(f"Data generation completed in {time.time() - start_time:.3f}s")

        # Insert data in batches
        logging.info("Inserting items...")
        start_time = time.time()
        await _insert_items_in_batches(mongodb_item_repo, items, batch_size=10_000)
        logging.info(f"Items inserted in {time.time() - start_time:.3f}s")

        logging.info("Inserting interactions...")
        start_time = time.time()
        await _insert_interactions_in_batches(mongodb_item_repo, interactions, batch_size=10_000)
        logging.info(f"Interactions inserted in {time.time() - start_time:.3f}s")

        logging.info("Test 1: Find 100 items without interactions")
        await _test_find_items_scenario(
            test_name="without_interactions",
            repo=mongodb_item_repo,
            criteria=ItemFilterCriteria(
                interactions=AnyItemInteraction(without_interactions=True),
                interactions_from_user=user_uuid,
            ),
            limit=100,
            check_items_result=False,
            max_expected_time=baseline_time * 15.0,
        )

        logging.info("Test 2: Find 100 viewed items")
        await _test_find_items_scenario(
            test_name="viewed_items",
            repo=mongodb_item_repo,
            criteria=ItemFilterCriteria(
                interactions=AnyItemInteraction(viewed=True),
                interactions_from_user=user_uuid,
            ),
            limit=100,
            check_items_result=False,
            max_expected_time=baseline_time * 15.0,
        )

        logging.info("Test 3: Find 100 any items (no filter)")
        await _test_find_items_scenario(
            test_name="any_items",
            repo=mongodb_item_repo,
            criteria=ItemFilterCriteria(),
            limit=100,
            check_items_result=True,
            max_expected_time=baseline_time * 1.5,
        )


async def _generate_items(count: int) -> list[Item]:
    """Generate test items"""
    items = []
    base_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(count):
        item = mock_item(
            item_uuid=uuid4(),
            name=f"Test Item {i}",
            description=f"Description for item {i}",
            published_at=base_date,
            created_at=base_date,
            updated_at=base_date,
            provider=ItemProvider.YOUTUBE,
        )
        items.append(item)

    return items


async def _generate_interactions(items: list[Item], user_uuid: UUID, count: int) -> list[Interaction]:
    """Generate test interactions"""
    if not items or count == 0:
        return []

    interactions = []
    interaction_types = [InteractionType.VIEWED, InteractionType.RECOMMENDED,
                        InteractionType.DISCOURAGED, InteractionType.HIDDEN]

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
        batch = items[i:i + batch_size]
        await repo.upsert_items(batch)

        if (i // batch_size + 1) % 10 == 0:  # Progress indicator every 10 batches
            logging.info(f"  Inserted {min(i + batch_size, len(items)):,} / {len(items):,} items")


async def _insert_interactions_in_batches(repo: ItemRepository, interactions: list[Interaction], batch_size: int) -> None:
    """Insert interactions in batches"""
    for i in range(0, len(interactions), batch_size):
        batch = interactions[i:i + batch_size]

        # Insert interactions one by one as the repository doesn't support batch insert
        tasks = []
        for interaction in batch:
            tasks.append(repo.add_interaction(interaction))

        await asyncio.gather(*tasks)

        if (i // batch_size + 1) % 10 == 0:  # Progress indicator every 10 batches
            logging.info(f"  Inserted {min(i + batch_size, len(interactions)):,} / {len(interactions):,} interactions")


async def _test_find_items_scenario(
    test_name: str,
    repo: ItemRepository,
    criteria: ItemFilterCriteria,
    limit: int,
    check_items_result: bool,
    max_expected_time: float,
) -> None:
    """Test a specific find_items scenario and measure performance"""
    # Warmup run
    await repo.find_items(criteria, 0, limit)

    # Performance test - run 3 times and take average
    times = []
    for run in range(3):
        start_time = time.time()
        results = await repo.find_items(criteria, 0, limit)
        end_time = time.time()

        execution_time = end_time - start_time
        times.append(execution_time)

        logging.info(f"  Run {run + 1}: Found {len(results)} items in {execution_time:.3f}s")

        # Verify we got some results for scenarios that should return data
        if check_items_result:
            assert len(results) > 0, f"Expected results for {test_name} but got none"

    avg_time = sum(times) / len(times)
    logging.info(f"  Average time for {test_name}: {avg_time:.3f}s, max expected {max_expected_time:.3f}s")

    assert avg_time < max_expected_time, (
        f"Average time for {test_name} ({avg_time:.3f}s) exceeded baseline "
        f"({max_expected_time:.3f}s)"
    )


def baseline_function() -> int:
    """
    A simple function to establish a baseline for performance.

    It takes around 60ms to execute on a 3.8GHz CPU.
    """
    total = 0
    for i in range(1000000):
        total += i
    return total
