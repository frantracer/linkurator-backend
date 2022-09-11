import uuid
from ipaddress import IPv4Address

import pytest

from linkurator_core.domain.interaction import Interaction, InteractionType
from linkurator_core.infrastructure.mongodb.interaction_repository import MongoDBInteractionRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="interaction_repo", scope="session")
def fixture_interaction_repo(db_name) -> MongoDBInteractionRepository:
    return MongoDBInteractionRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


def test_exception_is_raised_if_items_collection_is_not_created():
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        MongoDBInteractionRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")


def test_get_interaction(interaction_repo):
    interaction = Interaction.new(
        uuid=uuid.UUID("74cf7cb9-e86e-4d7d-9bb8-3881dc2ebd82"),
        item_uuid=uuid.UUID("77c0d137-b8d7-4424-836f-d9f4b546f2e9"),
        user_uuid=uuid.UUID("3b1b3369-f7f7-4f61-926f-bdbe3c49160a"),
        interaction_type=InteractionType.RECOMMENDED
    )
    interaction_repo.add(interaction)
    assert interaction_repo.get(interaction.uuid) == interaction


def test_delete_interaction(interaction_repo):
    interaction = Interaction.new(
        uuid=uuid.UUID("20e413a1-4600-4c7e-bab8-bb692ec51921"),
        user_uuid=uuid.UUID("60f53698-9cc6-47e5-994c-25c6cded6f62"),
        item_uuid=uuid.UUID("3ee43c65-2792-4c04-bc63-b3952988d954"),
        interaction_type=InteractionType.RECOMMENDED
    )
    interaction_repo.add(interaction)
    assert interaction_repo.get(interaction.uuid) is not None

    interaction_repo.delete(interaction.uuid)
    assert interaction_repo.get(interaction.uuid) is None


def test_get_interactions_by_item(interaction_repo):
    interaction0 = Interaction.new(
        uuid=uuid.UUID("99f8c2ce-bc34-45ed-8368-139033acf32e"),
        user_uuid=uuid.UUID("22bb661b-f298-435e-9bab-0e9a24c18638"),
        item_uuid=uuid.UUID("e29bf8f6-639e-4eb0-9d1e-fd452a7e6c3d"),
        interaction_type=InteractionType.RECOMMENDED,
    )

    interaction1 = Interaction.new(
        uuid=uuid.UUID("7b4eee4a-95a6-47af-9cf1-46f5a23cbde7"),
        user_uuid=uuid.UUID("e306a421-e191-4f50-874d-1f9e78e13694"),
        item_uuid=uuid.UUID("581402ec-8043-4098-9995-735e9e427571"),
        interaction_type=InteractionType.RECOMMENDED
    )
    interaction_repo.add(interaction1)

    interactions = interaction_repo.get_user_interactions_by_item_id(
        user_id=interaction1.user_uuid,
        item_ids=[interaction0.item_uuid, interaction1.item_uuid])

    assert interaction0.item_uuid in interactions
    assert interactions[interaction0.item_uuid] == []
    assert interaction1.item_uuid in interactions
    assert interactions[interaction1.item_uuid] == [interaction1]
