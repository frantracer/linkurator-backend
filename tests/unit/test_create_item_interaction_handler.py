from datetime import datetime, timezone
from uuid import UUID

import pytest

from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository


@pytest.mark.asyncio()
async def test_recommend_item_creates_interaction_and_mark_as_viewed() -> None:
    dummy_item = mock_item(
        item_uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
    )
    user_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([dummy_item])

    recommend_interaction = Interaction.new(
        uuid=UUID("b02c962e-7466-4028-8c72-503821d637a5"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)

    viewed_interaction = Interaction(
        uuid=UUID("483d7528-6b4c-437d-9b0e-59376bfa0953"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2021, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
    )

    handler = CreateItemInteractionHandler(
        item_repository=item_repo,
        uuid_generator=lambda: viewed_interaction.uuid,
        date_generator=lambda: viewed_interaction.created_at,
    )

    await handler.handle(recommend_interaction)

    # Verify both interactions were created
    stored_recommend = await item_repo.get_interaction(recommend_interaction.uuid)
    stored_viewed = await item_repo.get_interaction(viewed_interaction.uuid)
    assert stored_recommend is not None
    assert stored_viewed is not None
    assert stored_recommend.type == InteractionType.RECOMMENDED
    assert stored_viewed.type == InteractionType.VIEWED


@pytest.mark.asyncio()
async def test_discourage_item_creates_interaction_and_mark_as_viewed() -> None:
    dummy_item = mock_item(
        item_uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
    )
    user_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([dummy_item])

    discourage_interaction = Interaction.new(
        uuid=UUID("b02c962e-7466-4028-8c72-503821d637a5"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.DISCOURAGED)

    viewed_interaction = Interaction(
        uuid=UUID("483d7528-6b4c-437d-9b0e-59376bfa0953"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2021, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
    )

    handler = CreateItemInteractionHandler(
        item_repository=item_repo,
        uuid_generator=lambda: viewed_interaction.uuid,
        date_generator=lambda: viewed_interaction.created_at,
    )

    await handler.handle(discourage_interaction)

    # Verify both interactions were created
    stored_discourage = await item_repo.get_interaction(discourage_interaction.uuid)
    stored_viewed = await item_repo.get_interaction(viewed_interaction.uuid)
    assert stored_discourage is not None
    assert stored_viewed is not None
    assert stored_discourage.type == InteractionType.DISCOURAGED
    assert stored_viewed.type == InteractionType.VIEWED


@pytest.mark.asyncio()
async def test_recommend_item_that_already_is_viewed_only_creates_one_interaction() -> None:
    dummy_item = mock_item(
        item_uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
    )
    user_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([dummy_item])

    # Add existing viewed interaction
    existing_viewed = Interaction.new(
        uuid=UUID("b02c962e-7466-4028-8c72-503821d637a5"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.VIEWED)
    await item_repo.add_interaction(existing_viewed)

    recommend_interaction = Interaction.new(
        uuid=UUID("c02c962e-7466-4028-8c72-503821d637a6"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)

    viewed_interaction = Interaction(
        uuid=UUID("483d7528-6b4c-437d-9b0e-59376bfa0953"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2021, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
    )

    handler = CreateItemInteractionHandler(
        item_repository=item_repo,
        uuid_generator=lambda: viewed_interaction.uuid,
        date_generator=lambda: viewed_interaction.created_at,
    )

    await handler.handle(recommend_interaction)

    # Verify only the recommend interaction was added, not a new viewed interaction
    stored_recommend = await item_repo.get_interaction(recommend_interaction.uuid)
    stored_new_viewed = await item_repo.get_interaction(viewed_interaction.uuid)
    assert stored_recommend is not None
    assert stored_new_viewed is None  # Should not be added since item was already viewed


@pytest.mark.asyncio()
async def test_create_item_interaction_handler_with_existing_interaction_does_nothing() -> None:
    dummy_item = Item.new(
        uuid=UUID("9d0b1abf-4fb8-469a-80a3-6df4ae84cd96"),
        subscription_uuid=UUID("a74efb1b-830d-49ff-85c9-15e68b055725"),
        provider="youtube",
        thumbnail=utils.parse_url("https://example.com/thumbnail.jpg"),
        url=utils.parse_url("https://example.com"),
        name="Item 1",
        description="Item 1 description",
        published_at=datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
    )

    user_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    dummy_interaction = Interaction.new(
        uuid=UUID("c1ecc7f4-8555-4696-8650-3feb5958e2da"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([dummy_item])
    await item_repo.add_interaction(dummy_interaction)

    # Try to add the same interaction type from the same user again
    new_interaction = Interaction.new(
        uuid=UUID("05645afe-5b02-4c3f-b0ce-37bd955bab24"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(item_repository=item_repo)

    await handler.handle(new_interaction)

    # Verify the new interaction was not added since user already has this interaction type
    stored_new_interaction = await item_repo.get_interaction(new_interaction.uuid)
    interactions = await item_repo.get_user_interactions_by_item_id(user_id, [dummy_item.uuid])
    assert stored_new_interaction is None
    assert len(interactions[dummy_item.uuid]) == 1  # Only the original interaction


@pytest.mark.asyncio()
async def test_create_item_interaction_handler_with_non_existing_item_raises_an_error() -> None:
    item_repo = InMemoryItemRepository()

    new_interaction = Interaction.new(
        uuid=UUID("c1ecc7f4-8555-4696-8650-3feb5958e2da"),
        item_uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
        user_uuid=UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b"),
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(item_repository=item_repo)

    with pytest.raises(ItemNotFoundError):
        await handler.handle(new_interaction)


@pytest.mark.asyncio()
async def test_recommend_an_item_removes_discouraged_interaction() -> None:
    dummy_item = mock_item(
        item_uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
    )
    user_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([dummy_item])

    # Add existing discouraged interaction
    existing_discouraged = Interaction.new(
        uuid=UUID("b02c962e-7466-4028-8c72-503821d637a5"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.DISCOURAGED)
    await item_repo.add_interaction(existing_discouraged)

    recommend_interaction = Interaction.new(
        uuid=UUID("c02c962e-7466-4028-8c72-503821d637a6"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(
        item_repository=item_repo,
    )

    await handler.handle(recommend_interaction)

    # Verify the discouraged interaction was removed
    stored_discouraged = await item_repo.get_user_interactions_by_item_id(
        user_id=user_id,
        item_ids=[dummy_item.uuid],
    )
    interaction_types = [interaction.type for interaction in stored_discouraged.get(dummy_item.uuid, [])]
    assert InteractionType.DISCOURAGED not in interaction_types
    assert InteractionType.RECOMMENDED in interaction_types


@pytest.mark.asyncio()
async def test_discourage_an_item_removes_recommended_interaction() -> None:
    dummy_item = mock_item(
        item_uuid=UUID("76095094-994f-40f0-a1cb-b0bf438f3fd6"),
    )
    user_id = UUID("3b434473-c6b4-4c6a-a5f8-a5c22021ee3b")

    item_repo = InMemoryItemRepository()
    await item_repo.upsert_items([dummy_item])

    # Add existing recommended interaction
    existing_recommended = Interaction.new(
        uuid=UUID("b02c962e-7466-4028-8c72-503821d637a5"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)
    await item_repo.add_interaction(existing_recommended)

    discourage_interaction = Interaction.new(
        uuid=UUID("c02c962e-7466-4028-8c72-503821d637a6"),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.DISCOURAGED)

    handler = CreateItemInteractionHandler(
        item_repository=item_repo,
    )

    await handler.handle(discourage_interaction)

    # Verify the recommended interaction was removed
    stored_recommended = await item_repo.get_user_interactions_by_item_id(
        user_id=user_id,
        item_ids=[dummy_item.uuid],
    )
    interaction_types = [interaction.type for interaction in stored_recommended.get(dummy_item.uuid, [])]
    assert InteractionType.RECOMMENDED not in interaction_types
    assert InteractionType.DISCOURAGED in interaction_types
