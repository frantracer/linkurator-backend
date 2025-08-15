import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.chats.delete_chat_handler import DeleteChatHandler
from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.chats.chat_repository import ChatRepository


@pytest.fixture(name="chat_repository")
def chat_repository_fixture() -> AsyncMock:
    return AsyncMock(spec=ChatRepository)


@pytest.mark.asyncio()
async def test_delete_chat_handler_success(chat_repository: AsyncMock) -> None:
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Setup mock chat that belongs to the user
    now = datetime.now(timezone.utc)
    mock_chat_obj = Chat(
        uuid=chat_id,
        user_id=user_id,
        title="Test Chat",
        messages=[],
        created_at=now,
        updated_at=now,
    )
    chat_repository.get.return_value = mock_chat_obj

    handler = DeleteChatHandler(chat_repository=chat_repository)

    result = await handler.handle(chat_id=chat_id, user_id=user_id)

    assert result is True
    chat_repository.get.assert_called_once_with(chat_id)
    chat_repository.delete.assert_called_once_with(chat_id)


@pytest.mark.asyncio()
async def test_delete_chat_handler_chat_not_found(chat_repository: AsyncMock) -> None:
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Setup mock to return None (chat not found)
    chat_repository.get.return_value = None

    handler = DeleteChatHandler(chat_repository=chat_repository)

    result = await handler.handle(chat_id=chat_id, user_id=user_id)

    assert result is False
    chat_repository.get.assert_called_once_with(chat_id)
    chat_repository.delete.assert_not_called()


@pytest.mark.asyncio()
async def test_delete_chat_handler_chat_belongs_to_different_user(
    chat_repository: AsyncMock,
) -> None:
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Setup mock chat that belongs to a different user
    now = datetime.now(timezone.utc)
    mock_chat_obj = Chat(
        uuid=chat_id,
        user_id=other_user_id,
        title="Test Chat",
        messages=[],
        created_at=now,
        updated_at=now,
    )
    chat_repository.get.return_value = mock_chat_obj

    handler = DeleteChatHandler(chat_repository=chat_repository)

    result = await handler.handle(chat_id=chat_id, user_id=user_id)

    assert result is False
    chat_repository.get.assert_called_once_with(chat_id)
    chat_repository.delete.assert_not_called()
