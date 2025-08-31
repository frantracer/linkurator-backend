import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from linkurator_core.application.subscriptions.summarize_subscription_handler import SummarizeSubscriptionHandler
from linkurator_core.domain.agents.summarize_agent_service import SummarizeAgentResult, SummarizeAgentService
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio()
async def test_summarize_subscription_handler_updates_subscription_with_existing_summary() -> None:
    """Test that handler updates subscriptions even if they already have summaries."""
    subscription_repository = InMemorySubscriptionRepository()
    summarizer_service = AsyncMock(spec=SummarizeAgentService)
    mock_result = SummarizeAgentResult(
        summary="New generated summary",
    )
    summarizer_service.summarize.return_value = mock_result

    # Add subscription with existing summary
    subscription = mock_sub(
        summary="Existing summary",
    )
    await subscription_repository.add(subscription)
    original_updated_at = subscription.updated_at

    handler = SummarizeSubscriptionHandler(
        subscription_repository=subscription_repository,
        summarizer_service=summarizer_service,
    )

    # Small delay to ensure updated_at timestamp will be different
    await asyncio.sleep(0.001)
    await handler.handle(subscription.uuid)

    # Verify that summarizer service was called
    assert summarizer_service.summarize.call_count == 1

    # Verify that subscription was updated with new summary
    updated_subscription = await subscription_repository.get(subscription.uuid)
    assert updated_subscription is not None
    assert updated_subscription.summary == "New generated summary"
    assert updated_subscription.updated_at > original_updated_at


@pytest.mark.asyncio()
async def test_summarize_subscription_handler_handles_nonexistent_subscription() -> None:
    """Test that handler gracefully handles requests for non-existent subscriptions."""
    subscription_repository = InMemorySubscriptionRepository()
    summarizer_service = AsyncMock(spec=SummarizeAgentService)

    handler = SummarizeSubscriptionHandler(
        subscription_repository=subscription_repository,
        summarizer_service=summarizer_service,
    )

    # Use non-existent subscription ID
    non_existent_id = uuid4()

    # Should not raise an exception
    await handler.handle(non_existent_id)

    # Verify that summarizer service was NOT called
    assert summarizer_service.summarize.call_count == 0


@pytest.mark.asyncio()
async def test_summarize_subscription_handler_handles_summarizer_service_exception() -> None:
    """Test that handler gracefully handles exceptions from summarizer service."""
    subscription_repository = InMemorySubscriptionRepository()
    summarizer_service = AsyncMock(spec=SummarizeAgentService)
    summarizer_service.summarize.side_effect = Exception("AI service error")

    # Add subscription without summary
    subscription = mock_sub(summary="Current summary")
    await subscription_repository.add(subscription)
    original_updated_at = subscription.updated_at

    handler = SummarizeSubscriptionHandler(
        subscription_repository=subscription_repository,
        summarizer_service=summarizer_service,
    )

    # Should not raise an exception
    await handler.handle(subscription.uuid)

    # Verify that summarizer service was called
    assert summarizer_service.summarize.call_count == 1

    # Verify that subscription was NOT updated (due to exception)
    updated_subscription = await subscription_repository.get(subscription.uuid)
    assert updated_subscription is not None
    assert updated_subscription.summary == "Current summary"
    assert updated_subscription.updated_at == original_updated_at
