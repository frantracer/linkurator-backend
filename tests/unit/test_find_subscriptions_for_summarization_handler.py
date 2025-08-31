from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.subscriptions.find_subscriptions_for_summarization_handler import (
    FindSubscriptionsForSummarizationHandler,
)
from linkurator_core.domain.common.event import SubscriptionNeedsSummarizationEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio()
async def test_find_subscriptions_for_summarization_publishes_events_for_subscriptions_without_summaries() -> None:
    """Test that handler finds subscriptions without summaries and publishes events for them."""
    subscription_repository = InMemorySubscriptionRepository()
    event_bus = AsyncMock(spec=EventBusService)

    # Add subscriptions - some with summaries, some without
    sub_with_summary = mock_sub()
    sub_with_summary = sub_with_summary.model_copy(update={"summary": "This is a summary"})
    sub_without_summary_1 = mock_sub()
    sub_without_summary_2 = mock_sub()
    sub_without_summary_2 = sub_without_summary_2.model_copy(update={"summary": ""})
    sub_without_summary_3 = mock_sub()

    await subscription_repository.add(sub_with_summary)
    await subscription_repository.add(sub_without_summary_1)
    await subscription_repository.add(sub_without_summary_2)
    await subscription_repository.add(sub_without_summary_3)

    handler = FindSubscriptionsForSummarizationHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus,
    )

    await handler.handle()

    # Verify that events were published for subscriptions without summaries
    assert event_bus.publish.call_count == 3

    published_subscription_ids = {
        call.args[0].subscription_id for call in event_bus.publish.call_args_list
    }

    expected_subscription_ids = {sub_without_summary_1.uuid, sub_without_summary_2.uuid, sub_without_summary_3.uuid}
    assert published_subscription_ids == expected_subscription_ids

    # Verify that all published events are of the correct type
    for call in event_bus.publish.call_args_list:
        event = call.args[0]
        assert isinstance(event, SubscriptionNeedsSummarizationEvent)


@pytest.mark.asyncio()
async def test_find_subscriptions_for_summarization_does_nothing_when_no_subscriptions_need_summarization() -> None:
    """Test that handler does nothing when all subscriptions have summaries."""
    subscription_repository = InMemorySubscriptionRepository()
    event_bus = AsyncMock(spec=EventBusService)

    # Add only subscriptions that already have summaries
    sub_with_summary_1 = mock_sub()
    sub_with_summary_1 = sub_with_summary_1.model_copy(update={"summary": "Summary 1"})
    sub_with_summary_2 = mock_sub()
    sub_with_summary_2 = sub_with_summary_2.model_copy(update={"summary": "Summary 2"})

    await subscription_repository.add(sub_with_summary_1)
    await subscription_repository.add(sub_with_summary_2)

    handler = FindSubscriptionsForSummarizationHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus,
    )

    await handler.handle()

    # Verify that no events were published
    assert event_bus.publish.call_count == 0


@pytest.mark.asyncio()
async def test_find_subscriptions_for_summarization_handles_empty_repository() -> None:
    """Test that handler handles empty subscription repository gracefully."""
    subscription_repository = InMemorySubscriptionRepository()
    event_bus = AsyncMock(spec=EventBusService)

    handler = FindSubscriptionsForSummarizationHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus,
    )

    await handler.handle()

    # Verify that no events were published
    assert event_bus.publish.call_count == 0


@pytest.mark.asyncio()
async def test_find_subscriptions_for_summarization_continues_on_event_bus_error() -> None:
    """Test that handler continues processing even if event publishing fails for some subscriptions."""
    subscription_repository = InMemorySubscriptionRepository()
    event_bus = AsyncMock(spec=EventBusService)

    # Set up event bus to fail on the second call
    event_bus.publish.side_effect = [None, Exception("Event bus error"), None]

    # Add subscriptions without summaries
    sub_without_summary_1 = mock_sub()
    sub_without_summary_2 = mock_sub()
    sub_without_summary_3 = mock_sub()

    await subscription_repository.add(sub_without_summary_1)
    await subscription_repository.add(sub_without_summary_2)
    await subscription_repository.add(sub_without_summary_3)

    handler = FindSubscriptionsForSummarizationHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus,
    )

    # Should not raise an exception despite event bus error
    await handler.handle()

    # Verify that all three publish calls were attempted
    assert event_bus.publish.call_count == 3
