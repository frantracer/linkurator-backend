from unittest.mock import MagicMock, call
from uuid import UUID

from linkurator_core.application.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.domain.interaction import InteractionType, Interaction
from linkurator_core.domain.interaction_repository import InteractionRepository


def test_delete_item_interaction_handler():
    interaction_repo_mock = MagicMock(spec=InteractionRepository)
    dummy_interaction = Interaction.new(
        uuid=UUID('8572d7bb-91e6-49ad-ac17-bf3c7ec76ece'),
        user_uuid=UUID('d79a9c85-40b3-4b78-8205-3b6f7de9b187'),
        item_uuid=UUID('45b2736a-9f26-483a-9b97-82de73b4af2f'),
        interaction_type=InteractionType.RECOMMENDED
    )
    interaction_repo_mock.get_user_interactions_by_item_id.return_value = {
        dummy_interaction.item_uuid: [dummy_interaction]
    }
    handler = DeleteItemInteractionHandler(interaction_repository=interaction_repo_mock)

    handler.handle(
        user_id=dummy_interaction.user_uuid,
        item_id=dummy_interaction.item_uuid,
        interaction_type=dummy_interaction.type
    )

    assert interaction_repo_mock.get_user_interactions_by_item_id.called
    assert interaction_repo_mock.delete.called
    assert interaction_repo_mock.delete.call_args == call(dummy_interaction.uuid)
