from datetime import timezone, datetime

import pytest

from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.domain.common.mock_factory import mock_user, mock_item, mock_interaction
from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository


@pytest.mark.asyncio
async def test_get_curator_items_handlers_returns_items_and_interactions_for_curator_and_user() -> None:
    user = mock_user()
    curator = mock_user()
    item = mock_item()
    interaction1 = mock_interaction(user_id=user.uuid,
                                    item_id=item.uuid,
                                    interaction_type=InteractionType.DISCOURAGED)
    interaction2 = mock_interaction(user_id=curator.uuid,
                                    item_id=item.uuid,
                                    interaction_type=InteractionType.RECOMMENDED)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(interaction1)
    await item_repo.add_interaction(interaction2)

    handler = GetCuratorItemsHandler(item_repo)

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        created_before=now,
        page_number=0,
        page_size=10,
        user_id=user.uuid,
        curator_id=curator.uuid,
    )

    assert len(response) == 1
    assert response[0].item.uuid == item.uuid
    assert response[0].user_interactions[0].type == InteractionType.DISCOURAGED
    assert response[0].curator_interactions[0].type == InteractionType.RECOMMENDED


@pytest.mark.asyncio
async def test_get_curator_items_handlers_returns_items_for_curator_with_no_interactions_if_user_is_none() -> None:
    curator = mock_user()
    item = mock_item()

    curator_recommendation = mock_interaction(
        user_id=curator.uuid,
        item_id=item.uuid,
        interaction_type=InteractionType.RECOMMENDED)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(curator_recommendation)

    handler = GetCuratorItemsHandler(item_repo)

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        created_before=now,
        page_number=0,
        page_size=10,
        curator_id=curator.uuid,
    )

    assert len(response) == 1
    assert response[0].item.uuid == item.uuid
    assert len(response[0].user_interactions) == 0
