from datetime import datetime, timezone
from unittest.mock import MagicMock, call
from uuid import UUID

import pytest

from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.interaction import InteractionType, Interaction
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository


@pytest.mark.asyncio
async def test_recommend_item_creates_interaction_and_mark_as_viewed() -> None:
    dummy_item = mock_item(
        item_uuid=UUID('76095094-994f-40f0-a1cb-b0bf438f3fd6'),
    )
    user_id = UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b')

    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.get_user_interactions_by_item_id = MagicMock(return_value={})
    item_repo_mock.get_item = MagicMock(return_value=dummy_item)

    recommend_interaction = Interaction.new(
        uuid=UUID('b02c962e-7466-4028-8c72-503821d637a5'),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)

    viewed_interaction = Interaction(
        uuid=UUID('483d7528-6b4c-437d-9b0e-59376bfa0953'),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2021, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    )

    handler = CreateItemInteractionHandler(
        item_repository=item_repo_mock,
        uuid_generator=lambda: viewed_interaction.uuid,
        date_generator=lambda: viewed_interaction.created_at
    )

    await handler.handle(recommend_interaction)

    assert item_repo_mock.get_item.called
    assert item_repo_mock.get_user_interactions_by_item_id.called

    assert call(recommend_interaction) in item_repo_mock.add_interaction.call_args_list
    assert call(viewed_interaction) in item_repo_mock.add_interaction.call_args_list


@pytest.mark.asyncio
async def test_discourage_item_creates_interaction_and_mark_as_viewed() -> None:
    dummy_item = mock_item(
        item_uuid=UUID('76095094-994f-40f0-a1cb-b0bf438f3fd6'),
    )
    user_id = UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b')

    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.get_user_interactions_by_item_id = MagicMock(return_value={})
    item_repo_mock.get_item = MagicMock(return_value=dummy_item)

    discourage_interaction = Interaction.new(
        uuid=UUID('b02c962e-7466-4028-8c72-503821d637a5'),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.DISCOURAGED)

    viewed_interaction = Interaction(
        uuid=UUID('483d7528-6b4c-437d-9b0e-59376bfa0953'),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2021, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    )

    handler = CreateItemInteractionHandler(
        item_repository=item_repo_mock,
        uuid_generator=lambda: viewed_interaction.uuid,
        date_generator=lambda: viewed_interaction.created_at
    )

    await handler.handle(discourage_interaction)

    assert item_repo_mock.get_item.called
    assert item_repo_mock.get_user_interactions_by_item_id.called

    assert call(discourage_interaction) in item_repo_mock.add_interaction.call_args_list
    assert call(viewed_interaction) in item_repo_mock.add_interaction.call_args_list


@pytest.mark.asyncio
async def test_recommend_item_that_already_is_viewed_only_creates_one_interaction() -> None:
    dummy_item = mock_item(
        item_uuid=UUID('76095094-994f-40f0-a1cb-b0bf438f3fd6'),
    )
    user_id = UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b')

    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.get_user_interactions_by_item_id = MagicMock(
        return_value={dummy_item.uuid: [Interaction.new(
            uuid=UUID('b02c962e-7466-4028-8c72-503821d637a5'),
            item_uuid=dummy_item.uuid,
            user_uuid=user_id,
            interaction_type=InteractionType.VIEWED)]})
    item_repo_mock.get_item = MagicMock(return_value=dummy_item)

    recommend_interaction = Interaction.new(
        uuid=UUID('b02c962e-7466-4028-8c72-503821d637a5'),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        interaction_type=InteractionType.RECOMMENDED)

    viewed_interaction = Interaction(
        uuid=UUID('483d7528-6b4c-437d-9b0e-59376bfa0953'),
        item_uuid=dummy_item.uuid,
        user_uuid=user_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2021, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    )

    handler = CreateItemInteractionHandler(
        item_repository=item_repo_mock,
        uuid_generator=lambda: viewed_interaction.uuid,
        date_generator=lambda: viewed_interaction.created_at
    )

    await handler.handle(recommend_interaction)

    assert item_repo_mock.get_item.called
    assert item_repo_mock.get_user_interactions_by_item_id.called

    assert call(recommend_interaction) in item_repo_mock.add_interaction.call_args_list
    assert item_repo_mock.add_interaction.call_count == 1


@pytest.mark.asyncio
async def test_create_item_interaction_handler_with_existing_interaction_does_nothing() -> None:
    dummy_item = Item.new(
        uuid=UUID('9d0b1abf-4fb8-469a-80a3-6df4ae84cd96'),
        subscription_uuid=UUID('a74efb1b-830d-49ff-85c9-15e68b055725'),
        thumbnail=utils.parse_url('https://example.com/thumbnail.jpg'),
        url=utils.parse_url('https://example.com'),
        name='Item 1',
        description='Item 1 description',
        published_at=datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    )

    dummy_interaction = Interaction.new(
        uuid=UUID('c1ecc7f4-8555-4696-8650-3feb5958e2da'),
        item_uuid=dummy_item.uuid,
        user_uuid=UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b'),
        interaction_type=InteractionType.RECOMMENDED)

    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.get_item = MagicMock(return_value=dummy_item)
    item_repo_mock.get_user_interactions_by_item_id = MagicMock(
        return_value={dummy_interaction.item_uuid: [dummy_interaction]})

    new_interaction = Interaction.new(
        uuid=UUID('05645afe-5b02-4c3f-b0ce-37bd955bab24'),
        item_uuid=dummy_item.uuid,
        user_uuid=UUID('5e397524-c041-44ff-8e06-b966759f13cb'),
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(item_repository=item_repo_mock)

    await handler.handle(new_interaction)

    assert item_repo_mock.get_item.called
    assert item_repo_mock.get_user_interactions_by_item_id.called
    assert item_repo_mock.add_interaction.call_count == 0


@pytest.mark.asyncio
async def test_create_item_interaction_handler_with_non_existing_item_raises_an_error() -> None:
    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.get_item = MagicMock(return_value=None)
    item_repo_mock.get_user_interactions_by_item_id = MagicMock(return_value={})

    new_interaction = Interaction.new(
        uuid=UUID('c1ecc7f4-8555-4696-8650-3feb5958e2da'),
        item_uuid=UUID('76095094-994f-40f0-a1cb-b0bf438f3fd6'),
        user_uuid=UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b'),
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(item_repository=item_repo_mock)

    with pytest.raises(ItemNotFoundError):
        await handler.handle(new_interaction)
