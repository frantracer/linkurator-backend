from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.domain.common.mock_factory import mock_item, mock_interaction
from linkurator_core.domain.items.item_repository import ItemRepository, AnyItemInteraction, ItemFilterCriteria


@pytest.mark.asyncio
async def test_get_subscriptions_items_returns_items_with_interactions() -> None:
    item_repo = MagicMock(spec=ItemRepository)
    item = mock_item()
    item_repo.find_items.return_value = [item]
    interaction = mock_interaction()
    item_repo.get_user_interactions_by_item_id.return_value = {item.uuid: [interaction]}
    handler = GetSubscriptionItemsHandler(item_repository=item_repo)

    result = await handler.handle(
        user_id=UUID('939e4e07-85dc-4cc5-958d-b22a3dfd4e0e'),
        subscription_id=UUID('818714d3-dfc4-4c7e-9760-d8f1f08d6d95'),
        created_before=datetime.fromtimestamp(1000, tz=timezone.utc),
        page_number=1,
        page_size=10,
        text_filter='text_filter',
        min_duration=10,
        max_duration=20,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True
    )

    item_repo.find_items.assert_called_once()
    item_repo.find_items.assert_called_with(
        criteria=ItemFilterCriteria(
            subscription_ids=[UUID('818714d3-dfc4-4c7e-9760-d8f1f08d6d95')],
            published_after=datetime.fromtimestamp(0, tz=timezone.utc),
            created_before=datetime.fromtimestamp(1000, tz=timezone.utc),
            text='text_filter',
            interactions_from_user=UUID('939e4e07-85dc-4cc5-958d-b22a3dfd4e0e'),
            min_duration=10,
            max_duration=20,
            interactions=AnyItemInteraction(
                without_interactions=True,
                recommended=True,
                discouraged=True,
                viewed=True,
                hidden=True
            ),
        ),
        page_number=1,
        limit=10
    )
    item_repo.get_user_interactions_by_item_id.assert_called_once()

    assert result == [(item, [interaction])]


@pytest.mark.asyncio
async def test_test_get_subscriptions_items_with_no_user_returns_no_interactions() -> None:
    item_repo = MagicMock(spec=ItemRepository)
    item = mock_item()
    item_repo.find_items.return_value = [item]
    handler = GetSubscriptionItemsHandler(item_repository=item_repo)

    result = await handler.handle(
        user_id=None,
        subscription_id=UUID('818714d3-dfc4-4c7e-9760-d8f1f08d6d95'),
        created_before=datetime.fromtimestamp(1000, tz=timezone.utc),
        page_number=1,
        page_size=10,
        text_filter='text_filter',
        min_duration=10,
        max_duration=20,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True
    )

    item_repo.find_items.assert_called_once()
    item_repo.get_user_interactions_by_item_id.assert_not_called()

    assert result == [(item, [])]
