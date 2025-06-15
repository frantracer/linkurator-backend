from uuid import UUID

import pytest

from linkurator_core.application.items.get_item_handler import GetItemHandler, GetItemResponse
from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.common.mock_factory import mock_interaction, mock_item, mock_sub
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository


@pytest.mark.asyncio()
async def test_get_item_with_interaction() -> None:
    sub = mock_sub()
    subscription_repository = InMemorySubscriptionRepository()
    await subscription_repository.add(sub)

    item1 = mock_item(sub_uuid=sub.uuid)
    interaction1 = mock_interaction(item_id=item1.uuid)
    item_repository = InMemoryItemRepository()
    await item_repository.upsert_items([item1])
    await item_repository.add_interaction(interaction1)

    handler = GetItemHandler(item_repository=item_repository, subscription_repository=subscription_repository)

    result = await handler.handle(item_id=item1.uuid, user_id=interaction1.user_uuid)

    assert result == GetItemResponse(item=item1, interactions=[interaction1], subscription=sub)


@pytest.mark.asyncio()
async def test_get_not_existing_item_returns_error() -> None:
    subscription_repository = InMemorySubscriptionRepository()
    item_repository = InMemoryItemRepository()

    handler = GetItemHandler(item_repository=item_repository, subscription_repository=subscription_repository)

    with pytest.raises(ItemNotFoundError):
        await handler.handle(item_id=UUID("e730d42d-a5e6-4705-9850-22b91df95429"),
                             user_id=UUID("0cb96f09-6b77-4351-a9f9-331026091c86"))
