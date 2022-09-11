from datetime import datetime, timezone
from unittest.mock import MagicMock, call
from uuid import UUID

import pytest

from linkurator_core.application.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.exceptions import ItemNotFoundError
from linkurator_core.common import utils
from linkurator_core.domain.interaction import InteractionType, Interaction
from linkurator_core.domain.interaction_repository import InteractionRepository
from linkurator_core.domain.item import Item
from linkurator_core.domain.item_repository import ItemRepository


def test_create_item_interaction_handler():
    item_repo_mock = MagicMock(spec=ItemRepository)
    dummy_item = Item.new(
        uuid=UUID('76095094-994f-40f0-a1cb-b0bf438f3fd6'),
        subscription_uuid=UUID('c1ecc7f4-8555-4696-8650-3feb5958e2da'),
        thumbnail=utils.parse_url('https://example.com/thumbnail.jpg'),
        url=utils.parse_url('https://example.com'),
        name='Item 1',
        description='Item 1 description',
        published_at=datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    )
    item_repo_mock.get = MagicMock(return_value=dummy_item)

    interaction_repo_mock = MagicMock(spec=InteractionRepository)
    interaction_repo_mock.get_user_interactions_by_item_id = MagicMock(return_value={})

    new_interaction = Interaction.new(
        uuid=UUID('c1ecc7f4-8555-4696-8650-3feb5958e2da'),
        item_uuid=dummy_item.uuid,
        user_uuid=UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b'),
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(
        item_repository=item_repo_mock,
        interaction_repository=interaction_repo_mock
    )

    handler.handle(new_interaction)

    assert item_repo_mock.get.called
    assert interaction_repo_mock.get_user_interactions_by_item_id.called
    assert interaction_repo_mock.add.call_args == call(new_interaction)


def test_create_item_interaction_handler_with_existing_interaction_does_nothing():
    item_repo_mock = MagicMock(spec=ItemRepository)
    dummy_item = Item.new(
        uuid=UUID('9d0b1abf-4fb8-469a-80a3-6df4ae84cd96'),
        subscription_uuid=UUID('a74efb1b-830d-49ff-85c9-15e68b055725'),
        thumbnail=utils.parse_url('https://example.com/thumbnail.jpg'),
        url=utils.parse_url('https://example.com'),
        name='Item 1',
        description='Item 1 description',
        published_at=datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    )
    item_repo_mock.get = MagicMock(return_value=dummy_item)

    interaction_repo_mock = MagicMock(spec=InteractionRepository)
    dummy_interaction = Interaction.new(
        uuid=UUID('c1ecc7f4-8555-4696-8650-3feb5958e2da'),
        item_uuid=dummy_item.uuid,
        user_uuid=UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b'),
        interaction_type=InteractionType.RECOMMENDED)
    interaction_repo_mock.get_user_interactions_by_item_id = MagicMock(
        return_value={dummy_interaction.item_uuid: [dummy_interaction]})

    new_interaction = Interaction.new(
        uuid=UUID('05645afe-5b02-4c3f-b0ce-37bd955bab24'),
        item_uuid=dummy_item.uuid,
        user_uuid=UUID('5e397524-c041-44ff-8e06-b966759f13cb'),
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(
        item_repository=item_repo_mock,
        interaction_repository=interaction_repo_mock
    )

    handler.handle(new_interaction)

    assert item_repo_mock.get.called
    assert interaction_repo_mock.get_user_interactions_by_item_id.called
    assert interaction_repo_mock.add.call_count == 0


def test_create_item_interaction_handler_with_non_existing_item_raises_an_error():
    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.get = MagicMock(return_value=None)

    interaction_repo_mock = MagicMock(spec=InteractionRepository)
    interaction_repo_mock.get_user_interactions_by_item_id = MagicMock(return_value={})

    new_interaction = Interaction.new(
        uuid=UUID('c1ecc7f4-8555-4696-8650-3feb5958e2da'),
        item_uuid=UUID('76095094-994f-40f0-a1cb-b0bf438f3fd6'),
        user_uuid=UUID('3b434473-c6b4-4c6a-a5f8-a5c22021ee3b'),
        interaction_type=InteractionType.RECOMMENDED)

    handler = CreateItemInteractionHandler(
        item_repository=item_repo_mock,
        interaction_repository=interaction_repo_mock
    )

    with pytest.raises(ItemNotFoundError):
        handler.handle(new_interaction)
