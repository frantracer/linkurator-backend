from datetime import timedelta

import pytest

from linkurator_core.application.items.get_subscription_items_handler import (
    GetSubscriptionItemsHandler,
    GetSubscriptionItemsResponse,
)
from linkurator_core.domain.common.mock_factory import mock_interaction, mock_item, mock_sub, mock_user
from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_get_subscriptions_items_returns_items_with_interactions() -> None:
    subscription_repo = InMemorySubscriptionRepository()
    sub = mock_sub()
    await subscription_repo.add(sub)

    item_repo = InMemoryItemRepository()
    user = mock_user()
    item = mock_item(sub_uuid=sub.uuid)
    interaction = mock_interaction(item_id=item.uuid, user_id=user.uuid)
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(interaction)

    handler = GetSubscriptionItemsHandler(
        item_repository=item_repo,
        subscription_repository=subscription_repo,
        user_repository=InMemoryUserRepository(),
    )

    result = await handler.handle(
        user_id=user.uuid,
        subscription_id=sub.uuid,
        created_before=item.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True,
    )

    assert result == GetSubscriptionItemsResponse(
        items=[ItemWithInteractions(item=item, subscription=sub, interactions=[interaction])],
        subscription=sub,
    )


@pytest.mark.asyncio()
async def test_test_get_subscriptions_items_with_no_user_returns_no_interactions() -> None:
    subscription_repo = InMemorySubscriptionRepository()
    sub = mock_sub()
    await subscription_repo.add(sub)

    item_repo = InMemoryItemRepository()
    item = mock_item(sub_uuid=sub.uuid)
    await item_repo.upsert_items([item])

    handler = GetSubscriptionItemsHandler(
        item_repository=item_repo,
        subscription_repository=subscription_repo,
        user_repository=InMemoryUserRepository(),
    )

    result = await handler.handle(
        user_id=None,
        subscription_id=sub.uuid,
        created_before=item.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert result == GetSubscriptionItemsResponse(
        items=[ItemWithInteractions(item=item, subscription=sub, interactions=[])],
        subscription=sub,
    )


@pytest.mark.asyncio()
async def test_get_subscription_items_returns_curator_interactions_for_followed_curators() -> None:
    curator = mock_user()
    user = mock_user(curators={curator.uuid})
    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)
    user_interaction = mock_interaction(item_id=item.uuid, user_id=user.uuid,
                                        interaction_type=InteractionType.VIEWED)
    curator_interaction = mock_interaction(item_id=item.uuid, user_id=curator.uuid,
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

    handler = GetSubscriptionItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    result = await handler.handle(
        user_id=user.uuid,
        subscription_id=sub.uuid,
        created_before=item.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert len(result.items) == 1
    assert result.items[0].interactions[0].type == InteractionType.VIEWED
    assert len(result.items[0].curator_interactions) == 1
    assert result.items[0].curator_interactions[0].curator == curator
    assert result.items[0].curator_interactions[0].interactions[0].type == InteractionType.RECOMMENDED
