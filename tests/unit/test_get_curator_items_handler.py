from datetime import timezone, datetime
from unittest.mock import AsyncMock, call
from uuid import UUID

import pytest

from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.domain.common.mock_factory import mock_user, mock_item, mock_interaction
from linkurator_core.domain.items.interaction import InteractionType, Interaction
from linkurator_core.domain.items.item_repository import ItemRepository, AnyItemInteraction, ItemFilterCriteria
from tests.tools import assert_calls_in_any_order


@pytest.mark.asyncio
async def test_get_curator_items_handlers_returns_items_and_interactions_for_curator_and_user() -> None:
    user = mock_user()
    curator = mock_user()
    item = mock_item()
    item_repo_mock = AsyncMock(spec=ItemRepository)
    item_repo_mock.find_items.return_value = [item]

    async def get_user_interactions_by_item_id(
            user_id: UUID, item_ids: list[UUID]  # pylint: disable=unused-argument
    ) -> dict[UUID, list[Interaction]]:
        if user_id == user.uuid:
            return {item.uuid: [mock_interaction(user_id=user_id, interaction_type=InteractionType.RECOMMENDED)]}
        if user_id == curator.uuid:
            return {item.uuid: [mock_interaction(user_id=user_id, interaction_type=InteractionType.DISCOURAGED)]}
        return {}

    item_repo_mock.get_user_interactions_by_item_id = AsyncMock(side_effect=get_user_interactions_by_item_id)

    handler = GetCuratorItemsHandler(item_repo_mock)

    now = datetime.now(tz=timezone.utc)
    response = await handler.handle(
        created_before=now,
        page_number=1,
        page_size=10,
        user_id=user.uuid,
        curator_id=curator.uuid,
        curator_interactions=[InteractionType.RECOMMENDED, InteractionType.DISCOURAGED]
    )

    assert len(response) == 1
    assert response[0].item.uuid == item.uuid
    assert response[0].user_interactions[0].type == InteractionType.RECOMMENDED
    assert response[0].curator_interactions[0].type == InteractionType.DISCOURAGED
    assert item_repo_mock.find_items.call_count == 1
    assert item_repo_mock.find_items.call_args == call(
        criteria=ItemFilterCriteria(
            created_before=now,
            interactions_from_user=curator.uuid,
            interactions=AnyItemInteraction(
                recommended=True,
                discouraged=True,
                viewed=False,
                hidden=False
            )
        ),
        page_number=1,
        limit=10
    )
    assert item_repo_mock.get_user_interactions_by_item_id.call_count == 2
    assert_calls_in_any_order(
        actual_calls=item_repo_mock.get_user_interactions_by_item_id.call_args_list,
        expected_calls=[
            call(user_id=user.uuid, item_ids=[item.uuid]),
            call(user_id=curator.uuid, item_ids=[item.uuid])
        ])
