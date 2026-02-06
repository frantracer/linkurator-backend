from datetime import datetime, timezone

import pytest

from linkurator_core.application.items.get_followed_curators_items_handler import GetFollowedCuratorsItemsHandler
from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.common.mock_factory import mock_interaction, mock_item, mock_sub, mock_user
from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_get_followed_curators_items_returns_items_from_followed_curators() -> None:
    user = mock_user()
    curator1 = mock_user()
    curator2 = mock_user()
    user.follow_curator(curator1.uuid)
    user.follow_curator(curator2.uuid)

    sub1 = mock_sub()
    sub2 = mock_sub()
    item1 = mock_item(sub_uuid=sub1.uuid)
    item2 = mock_item(sub_uuid=sub2.uuid)

    curator1_recommendation = mock_interaction(
        user_id=curator1.uuid,
        item_id=item1.uuid,
        interaction_type=InteractionType.RECOMMENDED,
    )
    curator2_recommendation = mock_interaction(
        user_id=curator2.uuid,
        item_id=item2.uuid,
        interaction_type=InteractionType.RECOMMENDED,
    )

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator1)
    await user_repo.add(curator2)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item1, item2])
    await item_repo.add_interaction(curator1_recommendation)
    await item_repo.add_interaction(curator2_recommendation)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub1)
    await sub_repo.add(sub2)

    handler = GetFollowedCuratorsItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        user_id=user.uuid,
        created_before=now,
        page_number=0,
        page_size=10,
    )

    assert len(response) == 2
    item_uuids = {r.item.uuid for r in response}
    assert item1.uuid in item_uuids
    assert item2.uuid in item_uuids


@pytest.mark.asyncio()
async def test_get_followed_curators_items_returns_user_interactions() -> None:
    user = mock_user()
    curator = mock_user()
    user.follow_curator(curator.uuid)

    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)

    curator_recommendation = mock_interaction(
        user_id=curator.uuid,
        item_id=item.uuid,
        interaction_type=InteractionType.RECOMMENDED,
    )
    user_view = mock_interaction(
        user_id=user.uuid,
        item_id=item.uuid,
        interaction_type=InteractionType.VIEWED,
    )

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(curator_recommendation)
    await item_repo.add_interaction(user_view)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    handler = GetFollowedCuratorsItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        user_id=user.uuid,
        created_before=now,
        page_number=0,
        page_size=10,
    )

    assert len(response) == 1
    assert response[0].item.uuid == item.uuid
    assert len(response[0].interactions) == 1
    assert response[0].interactions[0].type == InteractionType.VIEWED
    assert len(response[0].curator_interactions) == 1
    assert response[0].curator_interactions[0].type == InteractionType.RECOMMENDED


@pytest.mark.asyncio()
async def test_get_followed_curators_items_returns_curator_info() -> None:
    user = mock_user()
    curator = mock_user()
    user.follow_curator(curator.uuid)

    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)

    curator_recommendation = mock_interaction(
        user_id=curator.uuid,
        item_id=item.uuid,
        interaction_type=InteractionType.RECOMMENDED,
    )

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(curator_recommendation)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    handler = GetFollowedCuratorsItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        user_id=user.uuid,
        created_before=now,
        page_number=0,
        page_size=10,
    )

    assert len(response) == 1
    assert response[0].curator is not None
    assert response[0].curator.uuid == curator.uuid


@pytest.mark.asyncio()
async def test_get_followed_curators_items_returns_empty_if_no_curators_followed() -> None:
    user = mock_user()

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    item_repo = InMemoryItemRepository()
    sub_repo = InMemorySubscriptionRepository()

    handler = GetFollowedCuratorsItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        user_id=user.uuid,
        created_before=now,
        page_number=0,
        page_size=10,
    )

    assert len(response) == 0


@pytest.mark.asyncio()
async def test_get_followed_curators_items_raises_error_if_user_not_found() -> None:
    user = mock_user()

    user_repo = InMemoryUserRepository()
    item_repo = InMemoryItemRepository()
    sub_repo = InMemorySubscriptionRepository()

    handler = GetFollowedCuratorsItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    now = datetime.now(tz=timezone.utc)
    with pytest.raises(UserNotFoundError):
        await handler.handle(
            user_id=user.uuid,
            created_before=now,
            page_number=0,
            page_size=10,
        )


@pytest.mark.asyncio()
async def test_get_followed_curators_items_ignores_non_recommended_interactions() -> None:
    user = mock_user()
    curator = mock_user()
    user.follow_curator(curator.uuid)

    sub = mock_sub()
    item = mock_item(sub_uuid=sub.uuid)

    curator_discouraged = mock_interaction(
        user_id=curator.uuid,
        item_id=item.uuid,
        interaction_type=InteractionType.DISCOURAGED,
    )

    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([item])
    await item_repo.add_interaction(curator_discouraged)

    sub_repo = InMemorySubscriptionRepository()
    await sub_repo.add(sub)

    handler = GetFollowedCuratorsItemsHandler(
        item_repository=item_repo,
        subscription_repository=sub_repo,
        user_repository=user_repo,
    )

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        user_id=user.uuid,
        created_before=now,
        page_number=0,
        page_size=10,
    )

    assert len(response) == 0
