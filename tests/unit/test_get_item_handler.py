from datetime import timezone, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.application.items.get_item_handler import GetItemHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions


def test_get_item_with_interaction() -> None:
    item1 = Item.new(
        uuid=UUID("e730d42d-a5e6-4705-9850-22b91df95429"),
        subscription_uuid=UUID("cec49f90-444c-477b-9fa8-96a5f772f2f5"),
        thumbnail=utils.parse_url("https://example.com/thumbnail1.jpg"),
        description="Description 1",
        name="Item 1",
        url=utils.parse_url("https://example.com/item1"),
        published_at=datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
    )
    interaction1 = Interaction.new(
        uuid=UUID("e730d42d-a5e6-4705-9850-22b91df95429"),
        item_uuid=item1.uuid,
        interaction_type=InteractionType.VIEWED,
        user_uuid=UUID("0cb96f09-6b77-4351-a9f9-331026091c86")
    )

    mock_item_repository = MagicMock(spec=ItemRepository)
    mock_item_repository.get_item.return_value = item1
    mock_item_repository.get_user_interactions_by_item_id.return_value = {
        item1.uuid: [interaction1]
    }

    handler = GetItemHandler(item_repository=mock_item_repository)

    result = handler.handle(item_id=item1.uuid, user_id=interaction1.user_uuid)

    assert result == ItemWithInteractions(item1, [interaction1])


def test_get_not_existing_item_returns_error() -> None:
    mock_item_repository = MagicMock(spec=ItemRepository)
    mock_item_repository.get_item.return_value = None

    handler = GetItemHandler(item_repository=mock_item_repository)

    with pytest.raises(ItemNotFoundError):
        handler.handle(item_id=UUID("e730d42d-a5e6-4705-9850-22b91df95429"),
                       user_id=UUID("0cb96f09-6b77-4351-a9f9-331026091c86"))
