from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from linkurator_core.application.subscriptions.update_subscription_handler import UpdateSubscriptionHandler
from linkurator_core.domain.common.event import SubscriptionNeedsSummarizationEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio()
async def test_update_subscription_handler_successfully_updates_subscription() -> None:
    """Test that handler successfully updates a subscription."""
    # Arrange
    subscription_repository = InMemorySubscriptionRepository()
    subscription_service = AsyncMock(spec=SubscriptionService)
    event_bus = AsyncMock(spec=EventBusService)

    current_subscription = mock_sub(
        uuid=uuid4(),
        description="Old description",
        name="Original name",
    )
    updated_subscription = mock_sub(
        uuid=current_subscription.uuid,
        description="New description",
        name="Updated name",
    )

    await subscription_repository.add(current_subscription)
    subscription_service.get_subscription.return_value = updated_subscription

    handler = UpdateSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
    )

    # Act
    await handler.handle(current_subscription.uuid)

    # Assert
    stored_subscription = await subscription_repository.get(current_subscription.uuid)
    assert stored_subscription is not None
    assert stored_subscription.description == "New description"
    assert stored_subscription.name == "Updated name"
    event_bus.publish.assert_called_once()

    # Verify the event published is SubscriptionNeedsSummarizationEvent
    published_event = event_bus.publish.call_args[0][0]
    assert isinstance(published_event, SubscriptionNeedsSummarizationEvent)
    assert published_event.subscription_id == current_subscription.uuid


@pytest.mark.asyncio()
async def test_update_subscription_handler_does_not_publish_event_when_description_unchanged() -> None:
    """Test that handler does not publish summarization event when description is unchanged."""
    # Arrange
    subscription_repository = InMemorySubscriptionRepository()
    subscription_service = AsyncMock(spec=SubscriptionService)
    event_bus = AsyncMock(spec=EventBusService)

    current_subscription = mock_sub(
        uuid=uuid4(),
        description="Same description",
        name="Original name",
    )
    updated_subscription = mock_sub(
        uuid=current_subscription.uuid,
        description="Same description",
        name="Updated name",
    )

    await subscription_repository.add(current_subscription)
    subscription_service.get_subscription.return_value = updated_subscription

    handler = UpdateSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
    )

    # Act
    await handler.handle(current_subscription.uuid)

    # Assert
    event_bus.publish.assert_not_called()


@pytest.mark.asyncio()
async def test_update_subscription_handler_handles_nonexistent_current_subscription() -> None:
    """Test that handler gracefully handles when current subscription doesn't exist."""
    # Arrange
    subscription_repository = AsyncMock(spec=SubscriptionRepository)
    subscription_service = AsyncMock(spec=SubscriptionService)
    event_bus = AsyncMock(spec=EventBusService)

    subscription_id = uuid4()
    subscription_repository.get.return_value = None

    handler = UpdateSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
    )

    # Act
    await handler.handle(subscription_id)

    # Assert
    subscription_repository.get.assert_called_once_with(subscription_id)
    subscription_service.get_subscription.assert_not_called()
    subscription_repository.update.assert_not_called()
    event_bus.publish.assert_not_called()


@pytest.mark.asyncio()
async def test_update_subscription_handler_handles_nonexistent_updated_subscription() -> None:
    """Test that handler gracefully handles when subscription service returns None."""
    # Arrange
    subscription_repository = AsyncMock(spec=SubscriptionRepository)
    subscription_service = AsyncMock(spec=SubscriptionService)
    event_bus = AsyncMock(spec=EventBusService)

    current_subscription = mock_sub()
    subscription_repository.get.return_value = current_subscription
    subscription_service.get_subscription.return_value = None

    handler = UpdateSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=subscription_service,
        event_bus=event_bus,
    )

    # Act
    await handler.handle(current_subscription.uuid)

    # Assert
    subscription_repository.get.assert_called_once_with(current_subscription.uuid)
    subscription_service.get_subscription.assert_called_once_with(current_subscription.uuid)
    subscription_repository.update.assert_not_called()
    event_bus.publish.assert_not_called()
