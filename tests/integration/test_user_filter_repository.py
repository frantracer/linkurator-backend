import asyncio
import uuid
from datetime import datetime, timezone
from ipaddress import IPv4Address
from math import floor
from typing import Any
from unittest import mock
from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.common.mock_factory import mock_user_filter
from linkurator_core.domain.users.user_filter import UserFilter
from linkurator_core.domain.users.user_filter_repository import UserFilterRepository
from linkurator_core.infrastructure.in_memory.user_filter_repository import InMemoryUserFilterRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.user_filter_repository import (
    MongoDBUserFilter,
    MongoDBUserFilterRepository,
)


@pytest.fixture(name="user_filter_repo", scope="session", params=["mongodb", "in_memory"])
def fixture_user_filter_repo(db_name: str, request: Any) -> UserFilterRepository:
    if request.param == "mongodb":
        return MongoDBUserFilterRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")
    return InMemoryUserFilterRepository()


@pytest.mark.asyncio()
async def test_exception_is_raised_if_user_filters_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBUserFilterRepository(IPv4Address("127.0.0.1"), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio()
async def test_upsert_user_filter(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("679c6db9-a54e-4947-b825-57a96fb5f599")
    user_filter = UserFilter.new(
        user_id=user_id,
        text_filter="machine learning",
        min_duration=300,
        max_duration=3600,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=False,
        include_viewed_items=True,
        include_hidden_items=False,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.user_id == user_filter.user_id
    assert retrieved_filter.text_filter == user_filter.text_filter
    assert retrieved_filter.min_duration == user_filter.min_duration
    assert retrieved_filter.max_duration == user_filter.max_duration
    assert retrieved_filter.include_items_without_interactions == user_filter.include_items_without_interactions
    assert retrieved_filter.include_recommended_items == user_filter.include_recommended_items
    assert retrieved_filter.include_discouraged_items == user_filter.include_discouraged_items
    assert retrieved_filter.include_viewed_items == user_filter.include_viewed_items
    assert retrieved_filter.include_hidden_items == user_filter.include_hidden_items
    assert int(retrieved_filter.created_at.timestamp() * 100) == floor(user_filter.created_at.timestamp() * 100)
    assert int(retrieved_filter.updated_at.timestamp() * 100) == floor(user_filter.updated_at.timestamp() * 100)


@pytest.mark.asyncio()
async def test_get_user_filter_that_does_not_exist(user_filter_repo: UserFilterRepository) -> None:
    retrieved_filter = await user_filter_repo.get(uuid.UUID("c04c2880-6376-4fe1-a0bf-eac1ae0801ad"))

    assert retrieved_filter is None


@pytest.mark.asyncio()
async def test_get_user_filter_with_invalid_format_raises_an_exception(
    user_filter_repo: UserFilterRepository,
) -> None:
    # This test is MongoDB-specific as it tests MongoDB document format validation
    if isinstance(user_filter_repo, InMemoryUserFilterRepository):
        pytest.skip("Test specific to MongoDB implementation")

    user_filter_dict = MongoDBUserFilter(
        user_id=uuid.UUID("449e3bee-6f9b-4cbc-8a09-64a6fcface96"),
        text_filter="test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ).model_dump()
    user_filter_dict["user_id"] = "invalid_uuid"
    collection_mock = AsyncMock()
    collection_mock.find_one = AsyncMock(return_value=user_filter_dict)
    with mock.patch.object(MongoDBUserFilterRepository, "_collection", return_value=collection_mock):
        with pytest.raises(ValueError):
            await user_filter_repo.get(uuid.UUID("c0d59790-bb68-415b-9be5-79c3088aada0"))


@pytest.mark.asyncio()
async def test_delete_user_filter(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("1006a7a9-4c12-4475-9c4a-7c0f6c9f8eb3")
    user_filter = UserFilter.new(
        user_id=user_id,
        text_filter="python tutorials",
        min_duration=600,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)
    assert retrieved_filter is not None

    await user_filter_repo.delete(user_id)
    deleted_filter = await user_filter_repo.get(user_id)
    assert deleted_filter is None


@pytest.mark.asyncio()
async def test_update_user_filter_via_upsert(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("0a634935-2fca-4103-b036-94dfa5d3eeaa")
    user_filter = UserFilter.new(
        user_id=user_id,
        text_filter="original text",
        min_duration=300,
        include_discouraged_items=True,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)
    assert retrieved_filter is not None
    assert retrieved_filter.text_filter == "original text"

    # Update the filter
    user_filter.text_filter = "updated text"
    user_filter.min_duration = 600
    user_filter.include_discouraged_items = False
    await user_filter_repo.upsert(user_filter)

    updated_filter = await user_filter_repo.get(user_id)
    assert updated_filter is not None
    assert updated_filter.text_filter == "updated text"
    assert updated_filter.min_duration == 600
    assert updated_filter.include_discouraged_items is False


@pytest.mark.asyncio()
async def test_user_filter_with_all_none_optional_fields(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("bb43a19d-cb28-4634-8ca7-4a5f6539678c")
    user_filter = UserFilter.new(
        user_id=user_id,
        text_filter=None,
        min_duration=None,
        max_duration=None,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.user_id == user_id
    assert retrieved_filter.text_filter is None
    assert retrieved_filter.min_duration is None
    assert retrieved_filter.max_duration is None
    assert retrieved_filter.include_items_without_interactions is True
    assert retrieved_filter.include_recommended_items is True
    assert retrieved_filter.include_discouraged_items is True
    assert retrieved_filter.include_viewed_items is True
    assert retrieved_filter.include_hidden_items is True


@pytest.mark.asyncio()
async def test_user_filter_with_all_boolean_flags_false(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("18244f86-75ea-4420-abcb-3552a51289ea")
    user_filter = UserFilter.new(
        user_id=user_id,
        include_items_without_interactions=False,
        include_recommended_items=False,
        include_discouraged_items=False,
        include_viewed_items=False,
        include_hidden_items=False,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.include_items_without_interactions is False
    assert retrieved_filter.include_recommended_items is False
    assert retrieved_filter.include_discouraged_items is False
    assert retrieved_filter.include_viewed_items is False
    assert retrieved_filter.include_hidden_items is False


@pytest.mark.asyncio()
async def test_user_filter_updated_at_changes_on_update(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("c2d73a23-217b-4985-a4f6-7f5828daa964")
    user_filter = mock_user_filter(user_id=user_id, text_filter="initial")

    await user_filter_repo.upsert(user_filter)
    first_filter = await user_filter_repo.get(user_id)
    assert first_filter is not None
    first_updated_at = first_filter.updated_at

    # Wait a moment and update
    await asyncio.sleep(0.01)

    user_filter.text_filter = "updated"
    await user_filter_repo.upsert(user_filter)
    second_filter = await user_filter_repo.get(user_id)
    assert second_filter is not None

    # updated_at should have changed
    assert second_filter.updated_at > first_updated_at


@pytest.mark.asyncio()
async def test_user_filter_with_duration_range(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("4cef3a68-9ec0-48e8-a6de-a56dd3ba1adf")
    user_filter = UserFilter.new(
        user_id=user_id,
        min_duration=120,
        max_duration=7200,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.min_duration == 120
    assert retrieved_filter.max_duration == 7200


@pytest.mark.asyncio()
async def test_user_filter_with_text_filter_only(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("9cca4ef4-3940-4527-8789-f76673a3842b")
    user_filter = UserFilter.new(
        user_id=user_id,
        text_filter="artificial intelligence and neural networks",
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.text_filter == "artificial intelligence and neural networks"
    assert retrieved_filter.min_duration is None
    assert retrieved_filter.max_duration is None


@pytest.mark.asyncio()
async def test_delete_non_existent_user_filter(user_filter_repo: UserFilterRepository) -> None:
    non_existent_user_id = uuid.UUID("021991aa-f9da-4935-bf34-7ffc805e1465")

    # Should not raise an exception
    await user_filter_repo.delete(non_existent_user_id)

    # Verify it still doesn't exist
    retrieved_filter = await user_filter_repo.get(non_existent_user_id)
    assert retrieved_filter is None


@pytest.mark.asyncio()
async def test_delete_all_user_filters(user_filter_repo: UserFilterRepository) -> None:
    user_id_1 = uuid.UUID("cb7b18dc-15d8-46b4-bce6-7214fa1a988b")
    user_id_2 = uuid.UUID("eeff7d5b-6c6a-442d-86d4-0140c4212116")

    user_filter_1 = mock_user_filter(user_id=user_id_1)
    user_filter_2 = mock_user_filter(user_id=user_id_2)

    await user_filter_repo.upsert(user_filter_1)
    await user_filter_repo.upsert(user_filter_2)

    # Verify they exist
    assert await user_filter_repo.get(user_id_1) is not None
    assert await user_filter_repo.get(user_id_2) is not None

    # Delete all
    await user_filter_repo.delete_all()

    # Verify they're gone
    assert await user_filter_repo.get(user_id_1) is None
    assert await user_filter_repo.get(user_id_2) is None


@pytest.mark.asyncio()
async def test_upsert_preserves_created_at_on_update(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("c932c023-730f-4448-9022-854e64cff9ee")
    user_filter = mock_user_filter(user_id=user_id, text_filter="original")

    await user_filter_repo.upsert(user_filter)
    first_filter = await user_filter_repo.get(user_id)
    assert first_filter is not None
    original_created_at = first_filter.created_at

    # Wait a moment and update
    await asyncio.sleep(0.01)

    user_filter.text_filter = "updated"
    await user_filter_repo.upsert(user_filter)
    second_filter = await user_filter_repo.get(user_id)
    assert second_filter is not None

    # created_at should remain the same
    assert int(second_filter.created_at.timestamp() * 100) == floor(original_created_at.timestamp() * 100)


@pytest.mark.asyncio()
async def test_user_filter_edge_case_zero_duration(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("cc74dcf5-2f9d-40cd-a0b4-b06a154699c2")
    user_filter = UserFilter.new(
        user_id=user_id,
        min_duration=0,
        max_duration=0,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.min_duration == 0
    assert retrieved_filter.max_duration == 0


@pytest.mark.asyncio()
async def test_user_filter_with_special_characters_in_text(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("7cfc3dd0-b20b-462f-b474-0f2f5159a325")
    special_text = 'C++ & Python: "Hello World" (2024) #programming @dev'
    user_filter = UserFilter.new(
        user_id=user_id,
        text_filter=special_text,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.text_filter == special_text


@pytest.mark.asyncio()
async def test_user_filter_with_emoji_in_text(user_filter_repo: UserFilterRepository) -> None:
    user_id = uuid.UUID("12345678-1234-5678-9abc-123456789abc")
    emoji_text = "Machine Learning 🤖 and AI 🧠 tutorials"
    user_filter = UserFilter.new(
        user_id=user_id,
        text_filter=emoji_text,
    )

    await user_filter_repo.upsert(user_filter)
    retrieved_filter = await user_filter_repo.get(user_id)

    assert retrieved_filter is not None
    assert retrieved_filter.text_filter == emoji_text
