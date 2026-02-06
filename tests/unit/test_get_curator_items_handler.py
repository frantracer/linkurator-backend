from datetime import datetime, timezone

import pytest

from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.domain.common.mock_factory import mock_interaction, mock_item, mock_sub, mock_user
from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_get_curator_items_returns_curator_interactions_for_followed_curators() -> None:
    curator = mock_user()
    user = mock_user(curators={curator.uuid})
    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)
    user_interaction = mock_interaction(user_id=user.uuid, item_id=item.uuid,
                                        interaction_type=InteractionType.DISCOURAGED)
    curator_interaction = mock_interaction(user_id=curator.uuid, item_id=item.uuid,
                                           interaction_type=InteractionType.RECOMMENDED)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(user_interaction)
    await item_repo.add_interaction(curator_interaction)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    handler = GetCuratorItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    response = await handler.handle(
        created_before=datetime.now(tz=timezone.utc),
        page_number=0,
        page_size=10,
        user_id=user.uuid,
        curator_id=curator.uuid,
    )

    assert len(response) == 1
    assert response[0].item.uuid == item.uuid
    assert response[0].subscription == sub
    assert response[0].interactions[0].type == InteractionType.DISCOURAGED
    assert len(response[0].curator_interactions) == 1
    assert response[0].curator_interactions[0].curator == curator
    assert response[0].curator_interactions[0].interactions[0].type == InteractionType.RECOMMENDED


@pytest.mark.asyncio()
async def test_get_curator_items_returns_no_curator_interactions_if_user_does_not_follow_curator() -> None:
    curator = mock_user()
    user = mock_user(curators=set())
    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)
    curator_interaction = mock_interaction(user_id=curator.uuid, item_id=item.uuid,
                                           interaction_type=InteractionType.RECOMMENDED)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(curator_interaction)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    handler = GetCuratorItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    response = await handler.handle(
        created_before=datetime.now(tz=timezone.utc),
        page_number=0,
        page_size=10,
        user_id=user.uuid,
        curator_id=curator.uuid,
    )

    assert len(response) == 1
    assert response[0].item.uuid == item.uuid
    assert len(response[0].interactions) == 0
    assert len(response[0].curator_interactions) == 0


@pytest.mark.asyncio()
async def test_get_curator_items_returns_no_curator_interactions_if_no_user() -> None:
    curator = mock_user()
    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)
    curator_interaction = mock_interaction(user_id=curator.uuid, item_id=item.uuid,
                                           interaction_type=InteractionType.RECOMMENDED)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(curator_interaction)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    user_repo = InMemoryUserRepository()
    await user_repo.add(curator)

    handler = GetCuratorItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    response = await handler.handle(
        created_before=datetime.now(tz=timezone.utc),
        page_number=0,
        page_size=10,
        curator_id=curator.uuid,
    )

    assert len(response) == 1
    assert response[0].item.uuid == item.uuid
    assert len(response[0].interactions) == 0
    assert len(response[0].curator_interactions) == 0
