from datetime import timedelta

import pytest

from linkurator_core.application.items.get_followed_subscriptions_items_handler import (
    GetFollowedSubscriptionsItemsHandler,
    GetFollowedSubscriptionsItemsResponse,
)
from linkurator_core.domain.common.mock_factory import mock_interaction, mock_item, mock_sub, mock_user
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_get_followed_subscriptions_items_returns_items_with_interactions() -> None:
    subscription_repo = InMemorySubscriptionRepository()
    sub1 = mock_sub()
    sub2 = mock_sub()
    await subscription_repo.add(sub1)
    await subscription_repo.add(sub2)

    user_repo = InMemoryUserRepository()
    user = mock_user()
    user.follow_subscription(sub1.uuid)
    user.follow_subscription(sub2.uuid)
    await user_repo.add(user)

    item_repo = InMemoryItemRepository()
    item1 = mock_item(sub_uuid=sub1.uuid)
    item2 = mock_item(sub_uuid=sub2.uuid)
    interaction1 = mock_interaction(item_id=item1.uuid, user_id=user.uuid)
    interaction2 = mock_interaction(item_id=item2.uuid, user_id=user.uuid)
    await item_repo.upsert_items([item1, item2])
    await item_repo.add_interaction(interaction1)
    await item_repo.add_interaction(interaction2)

    handler = GetFollowedSubscriptionsItemsHandler(
        item_repository=item_repo,
        subscription_repository=subscription_repo,
        user_repository=user_repo,
    )

    result = await handler.handle(
        user_id=user.uuid,
        created_before=max(item1.created_at, item2.created_at) + timedelta(seconds=1),
        page_number=0,
        page_size=10,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True,
    )

    assert len(result.items) == 2

    # Find items by UUID since order might not be deterministic
    result_by_item_id = {item.item.uuid: item for item in result.items}

    assert item1.uuid in result_by_item_id
    assert item2.uuid in result_by_item_id

    assert result_by_item_id[item1.uuid] == ItemWithInteractions(
        item=item1,
        subscription=sub1,
        interactions=[interaction1],
    )
    assert result_by_item_id[item2.uuid] == ItemWithInteractions(
        item=item2,
        subscription=sub2,
        interactions=[interaction2],
    )


@pytest.mark.asyncio()
async def test_get_followed_subscriptions_items_with_no_followed_subscriptions_returns_empty() -> None:
    subscription_repo = InMemorySubscriptionRepository()
    sub = mock_sub()
    await subscription_repo.add(sub)

    user_repo = InMemoryUserRepository()
    user = mock_user()
    await user_repo.add(user)

    item_repo = InMemoryItemRepository()
    item = mock_item(sub_uuid=sub.uuid)
    await item_repo.upsert_items([item])

    handler = GetFollowedSubscriptionsItemsHandler(
        item_repository=item_repo,
        subscription_repository=subscription_repo,
        user_repository=user_repo,
    )

    result = await handler.handle(
        user_id=user.uuid,
        created_before=item.created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert result == GetFollowedSubscriptionsItemsResponse(items=[])


@pytest.mark.asyncio()
async def test_get_followed_subscriptions_items_with_nonexistent_user_returns_empty() -> None:
    subscription_repo = InMemorySubscriptionRepository()
    user_repo = InMemoryUserRepository()
    item_repo = InMemoryItemRepository()

    handler = GetFollowedSubscriptionsItemsHandler(
        item_repository=item_repo,
        subscription_repository=subscription_repo,
        user_repository=user_repo,
    )

    result = await handler.handle(
        user_id=mock_user().uuid,
        created_before=mock_item().created_at + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert result == GetFollowedSubscriptionsItemsResponse(items=[])


@pytest.mark.asyncio()
async def test_get_followed_subscriptions_items_filters_by_followed_subscriptions_only() -> None:
    subscription_repo = InMemorySubscriptionRepository()
    followed_sub = mock_sub()
    unfollowed_sub = mock_sub()
    await subscription_repo.add(followed_sub)
    await subscription_repo.add(unfollowed_sub)

    user_repo = InMemoryUserRepository()
    user = mock_user()
    user.follow_subscription(followed_sub.uuid)
    await user_repo.add(user)

    item_repo = InMemoryItemRepository()
    followed_item = mock_item(sub_uuid=followed_sub.uuid)
    unfollowed_item = mock_item(sub_uuid=unfollowed_sub.uuid)
    await item_repo.upsert_items([followed_item, unfollowed_item])

    handler = GetFollowedSubscriptionsItemsHandler(
        item_repository=item_repo,
        subscription_repository=subscription_repo,
        user_repository=user_repo,
    )

    result = await handler.handle(
        user_id=user.uuid,
        created_before=max(followed_item.created_at, unfollowed_item.created_at) + timedelta(seconds=1),
        page_number=0,
        page_size=10,
    )

    assert len(result.items) == 1
    assert result.items[0].item == followed_item
    assert result.items[0].subscription == followed_sub
