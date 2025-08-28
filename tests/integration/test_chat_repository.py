import time
import uuid
from datetime import datetime, timezone
from ipaddress import IPv4Address
from math import floor
from typing import Any

import pytest

from linkurator_core.domain.chats.chat import Chat, ChatRole
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.domain.common.mock_factory import mock_chat, mock_chat_message
from linkurator_core.infrastructure.in_memory.chat_repository import InMemoryChatRepository
from linkurator_core.infrastructure.mongodb.chat_repository import MongoDBChatRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="chat_repo", params=["mongodb", "in_memory"])
def fixture_chat_repo(db_name: str, request: Any) -> ChatRepository:
    if request.param == "in_memory":
        return InMemoryChatRepository()
    return MongoDBChatRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio()
async def test_exception_is_raised_if_chats_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBChatRepository(IPv4Address("127.0.0.1"), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio()
async def test_add_and_get_chat(chat_repo: ChatRepository) -> None:
    if hasattr(chat_repo, "delete_all"):
        await chat_repo.delete_all()

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    chat = Chat(
        uuid=chat_id,
        user_id=user_id,
        title="Test Chat",
        messages=[],
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )

    await chat_repo.add(chat)
    retrieved_chat = await chat_repo.get(chat_id)

    assert retrieved_chat is not None
    assert retrieved_chat.uuid == chat_id
    assert retrieved_chat.user_id == user_id
    assert retrieved_chat.title == "Test Chat"
    assert retrieved_chat.messages == chat.messages
    # Use floor comparison for datetime precision differences
    assert floor(retrieved_chat.created_at.timestamp() * 100) == floor(chat.created_at.timestamp() * 100)
    assert floor(retrieved_chat.updated_at.timestamp() * 100) == floor(chat.updated_at.timestamp() * 100)


@pytest.mark.asyncio()
async def test_get_nonexistent_chat(chat_repo: ChatRepository) -> None:
    nonexistent_id = uuid.uuid4()
    result = await chat_repo.get(nonexistent_id)

    assert result is None


@pytest.mark.asyncio()
async def test_add_chat_with_messages(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    messages = [
        mock_chat_message(role=ChatRole.USER, content="Hello"),
        mock_chat_message(role=ChatRole.ASSISTANT, content="Hi there!", topic_were_created=True),
    ]
    chat = mock_chat(uuid=chat_id, user_id=user_id, messages=messages)

    await chat_repo.add(chat)
    retrieved_chat = await chat_repo.get(chat_id)

    assert retrieved_chat is not None
    assert len(retrieved_chat.messages) == 2
    assert retrieved_chat.messages[0].role == ChatRole.USER
    assert retrieved_chat.messages[0].content == "Hello"
    assert retrieved_chat.messages[0].topic_were_created is False
    assert retrieved_chat.messages[1].role == ChatRole.ASSISTANT
    assert retrieved_chat.messages[1].content == "Hi there!"
    assert retrieved_chat.messages[1].topic_were_created is True


@pytest.mark.asyncio()
async def test_get_by_user_id_empty(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user_id = uuid.uuid4()
    chats = await chat_repo.get_by_user_id(user_id)

    assert chats == []


@pytest.mark.asyncio()
async def test_get_by_user_id_single_chat(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user_id = uuid.uuid4()
    chat = mock_chat(user_id=user_id, title="User's Chat")

    await chat_repo.add(chat)
    chats = await chat_repo.get_by_user_id(user_id)

    assert len(chats) == 1
    assert chats[0].user_id == user_id
    assert chats[0].title == "User's Chat"


@pytest.mark.asyncio()
async def test_get_by_user_id_multiple_chats(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    chat1 = mock_chat(user_id=user_id, title="Chat 1")
    chat2 = mock_chat(user_id=user_id, title="Chat 2")
    other_chat = mock_chat(user_id=other_user_id, title="Other Chat")

    await chat_repo.add(chat1)
    await chat_repo.add(chat2)
    await chat_repo.add(other_chat)

    user_chats = await chat_repo.get_by_user_id(user_id)
    other_user_chats = await chat_repo.get_by_user_id(other_user_id)

    assert len(user_chats) == 2
    assert len(other_user_chats) == 1

    user_titles = {chat.title for chat in user_chats}
    assert user_titles == {"Chat 1", "Chat 2"}
    assert other_user_chats[0].title == "Other Chat"


@pytest.mark.asyncio()
async def test_update_existing_chat(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    original_chat = Chat(
        uuid=chat_id,
        user_id=user_id,
        title="Original Title",
        messages=[],
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
    )

    await chat_repo.add(original_chat)

    # Modify the chat
    original_chat.update_title("Updated Title")
    original_chat.add_user_message("New message")
    original_chat.updated_at = datetime.fromtimestamp(1, tz=timezone.utc)

    await chat_repo.update(original_chat)
    updated_chat = await chat_repo.get(chat_id)

    assert updated_chat is not None
    assert updated_chat.title == "Updated Title"
    assert len(updated_chat.messages) == 1
    assert updated_chat.messages[0].content == "New message"
    assert floor(updated_chat.created_at.timestamp() * 100) == floor(original_chat.created_at.timestamp() * 100)
    assert floor(updated_chat.updated_at.timestamp() * 100) == floor(original_chat.updated_at.timestamp() * 100)


@pytest.mark.asyncio()
async def test_update_nonexistent_chat(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    nonexistent_chat = mock_chat(title="Nonexistent")

    # Should not raise an error
    await chat_repo.update(nonexistent_chat)

    # Verify it wasn't actually added
    result = await chat_repo.get(nonexistent_chat.uuid)
    assert result is None


@pytest.mark.asyncio()
async def test_delete_existing_chat(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    chat = mock_chat(title="To Delete")

    await chat_repo.add(chat)
    assert await chat_repo.get(chat.uuid) is not None

    await chat_repo.delete(chat.uuid)
    assert await chat_repo.get(chat.uuid) is None


@pytest.mark.asyncio()
async def test_delete_nonexistent_chat(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    nonexistent_id = uuid.uuid4()

    # Should not raise an error
    await chat_repo.delete(nonexistent_id)


@pytest.mark.asyncio()
async def test_delete_all_with_chats(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user1 = uuid.uuid4()
    user2 = uuid.uuid4()

    chat1 = mock_chat(user_id=user1, title="Chat 1")
    chat2 = mock_chat(user_id=user2, title="Chat 2")

    await chat_repo.add(chat1)
    await chat_repo.add(chat2)

    # Verify chats exist
    assert len(await chat_repo.get_by_user_id(user1)) == 1
    assert len(await chat_repo.get_by_user_id(user2)) == 1

    await chat_repo.delete_all()

    # Verify all chats are deleted
    assert len(await chat_repo.get_by_user_id(user1)) == 0
    assert len(await chat_repo.get_by_user_id(user2)) == 0
    assert await chat_repo.get(chat1.uuid) is None
    assert await chat_repo.get(chat2.uuid) is None


@pytest.mark.asyncio()
async def test_chat_with_complex_messages(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user_id = uuid.uuid4()
    item_id = uuid.uuid4()
    subscription_id = uuid.uuid4()
    topic_id = uuid.uuid4()

    # Create message with all optional fields
    message = mock_chat_message(
        role=ChatRole.ASSISTANT,
        content="Here are some recommendations",
        item_uuids=[item_id],
        subscription_uuids=[subscription_id],
        topic_uuids=[topic_id],
    )

    chat = mock_chat(user_id=user_id, messages=[message])

    await chat_repo.add(chat)
    retrieved_chat = await chat_repo.get(chat.uuid)

    assert retrieved_chat is not None
    assert len(retrieved_chat.messages) == 1

    retrieved_message = retrieved_chat.messages[0]
    assert retrieved_message.role == ChatRole.ASSISTANT
    assert retrieved_message.content == "Here are some recommendations"
    assert retrieved_message.item_uuids == [item_id]
    assert retrieved_message.subscription_uuids == [subscription_id]
    assert retrieved_message.topic_uuids == [topic_id]


@pytest.mark.asyncio()
async def test_concurrent_operations(chat_repo: ChatRepository) -> None:
    await chat_repo.delete_all()

    user_id = uuid.uuid4()

    # Create multiple chats for the same user
    chats = [mock_chat(user_id=user_id, title=f"Chat {i}") for i in range(5)]

    # Add all chats
    for chat in chats:
        await chat_repo.add(chat)

    # Verify all chats exist
    user_chats = await chat_repo.get_by_user_id(user_id)
    assert len(user_chats) == 5

    # Update all chats
    for chat in chats:
        chat.update_title(f"Updated {chat.title}")
        await chat_repo.update(chat)

    # Verify updates
    updated_chats = await chat_repo.get_by_user_id(user_id)
    for chat in updated_chats:
        assert chat.title.startswith("Updated")

    # Delete half the chats (indices 0, 2, 4)
    for i in range(0, 5, 2):
        await chat_repo.delete(chats[i].uuid)

    # Verify remaining chats (indices 1, 3 should remain)
    remaining_chats = await chat_repo.get_by_user_id(user_id)
    assert len(remaining_chats) == 2


@pytest.mark.asyncio()
async def test_mongodb_serialization_with_unicode_and_special_chars(chat_repo: ChatRepository) -> None:
    """Test serialization/deserialization with unicode and special characters."""
    await chat_repo.delete_all()

    user_id = uuid.uuid4()

    # Create a chat with complex data types that need proper serialization
    messages = [
        mock_chat_message(
            role=ChatRole.USER,
            content="Test with unicode: 🤖 éñ 中文",
        ),
        mock_chat_message(
            role=ChatRole.ASSISTANT,
            content="Response with special chars: <>&\"'",
            item_uuids=[uuid.uuid4(), uuid.uuid4()],
            subscription_uuids=[uuid.uuid4()],
            topic_uuids=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4()],
        ),
    ]

    chat = mock_chat(
        user_id=user_id,
        title="Test with special chars: <>&\"'",
        messages=messages,
    )

    await chat_repo.add(chat)
    retrieved_chat = await chat_repo.get(chat.uuid)

    assert retrieved_chat is not None
    assert retrieved_chat.title == "Test with special chars: <>&\"'"
    assert len(retrieved_chat.messages) == 2

    # Verify unicode content is preserved
    assert retrieved_chat.messages[0].content == "Test with unicode: 🤖 éñ 中文"
    assert retrieved_chat.messages[1].content == "Response with special chars: <>&\"'"

    # Verify UUIDs are properly serialized/deserialized
    assert len(retrieved_chat.messages[1].item_uuids) == 2
    assert len(retrieved_chat.messages[1].subscription_uuids) == 1
    assert len(retrieved_chat.messages[1].topic_uuids) == 3

    # Verify all UUIDs are properly typed
    for item_uuid in retrieved_chat.messages[1].item_uuids:
        assert isinstance(item_uuid, uuid.UUID)


@pytest.mark.asyncio()
async def test_get_by_user_id_sorted_by_updated_at(chat_repo: ChatRepository) -> None:
    """Test that chats are returned sorted by updated_at in descending order."""
    await chat_repo.delete_all()

    user_id = uuid.uuid4()

    # Create chats with different update times
    chat1 = mock_chat(user_id=user_id, title="First Chat")
    chat1.updated_at = datetime.now(timezone.utc)

    time.sleep(0.001)  # Ensure different timestamps

    chat2 = mock_chat(user_id=user_id, title="Second Chat")
    chat2.updated_at = datetime.now(timezone.utc)

    # Add in reverse order to test sorting
    await chat_repo.add(chat1)
    await chat_repo.add(chat2)

    chats = await chat_repo.get_by_user_id(user_id)

    assert len(chats) == 2
    # Should be sorted by updated_at desc, so chat2 (more recent) should be first
    assert chats[0].title == "Second Chat"
    assert chats[1].title == "First Chat"
