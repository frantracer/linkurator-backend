import uuid
from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.chats.query_agent_handler import QueryAgentHandler
from linkurator_core.domain.chats.chat import ChatRole
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import (
    InvalidChatError,
    MaxMessagePerChatError,
    MessageIsBeingProcessedError,
)
from linkurator_core.domain.common.mock_factory import (
    mock_chat,
    mock_chat_message,
)
from linkurator_core.infrastructure.in_memory.chat_repository import InMemoryChatRepository


@pytest.mark.asyncio()
async def test_query_agent_handler_new_chat() -> None:
    chat_repository = InMemoryChatRepository()
    event_bus = AsyncMock(spec=EventBusService)

    handler = QueryAgentHandler(
        chat_repository=chat_repository,
        event_bus=event_bus,
    )

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    query = "What should I watch today?"

    await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    # Verify chat was created
    created_chat = await chat_repository.get(chat_id)
    assert created_chat is not None
    assert created_chat.user_id == user_id
    assert len(created_chat.messages) == 1
    assert created_chat.messages[0].role == ChatRole.USER
    assert created_chat.messages[0].content == query

    # Verify event was published
    event_bus.publish.assert_called_once()
    assert event_bus.publish.call_args[0][0].chat_id == chat_id
    assert event_bus.publish.call_args[0][0].query == query


@pytest.mark.asyncio()
async def test_query_agent_handler_existing_chat_with_messages() -> None:
    chat_repository = InMemoryChatRepository()
    event_bus = AsyncMock(spec=EventBusService)

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Create a chat with 2 user messages (under the limit)
    existing_chat = mock_chat(
        uuid=chat_id,
        user_id=user_id,
        messages=[
            mock_chat_message(role=ChatRole.USER, content="First query"),
            mock_chat_message(role=ChatRole.ASSISTANT, content="First response"),
            mock_chat_message(role=ChatRole.USER, content="Second query"),
            mock_chat_message(role=ChatRole.ASSISTANT, content="Second response"),
        ],
    )

    await chat_repository.add(existing_chat)

    handler = QueryAgentHandler(
        chat_repository=chat_repository,
        event_bus=event_bus,
    )

    query = "Third query should work"
    await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    # Verify chat was updated with new messages
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None
    assert len(updated_chat.messages) == 5  # Original 4 + 1 new messages
    assert updated_chat.messages[-1].role == ChatRole.USER
    assert updated_chat.messages[-1].content == query


@pytest.mark.asyncio()
async def test_query_agent_handler_rate_limit_exactly_5_queries() -> None:
    chat_repository = InMemoryChatRepository()
    event_bus = AsyncMock(spec=EventBusService)

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Create a chat with exactly 5 user messages (at the limit)
    messages = []
    for i in range(5):
        messages.append(mock_chat_message(role=ChatRole.USER, content=f"Query {i + 1}"))
        messages.append(mock_chat_message(role=ChatRole.ASSISTANT, content=f"Response {i + 1}"))

    existing_chat = mock_chat(
        uuid=chat_id,
        user_id=user_id,
        messages=messages,
    )

    await chat_repository.add(existing_chat)

    handler = QueryAgentHandler(
        chat_repository=chat_repository,
        event_bus=event_bus,
    )

    query = "Sixth query should be blocked"

    with pytest.raises(MaxMessagePerChatError):
        await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    # Verify chat was not modified
    unchanged_chat = await chat_repository.get(chat_id)
    assert unchanged_chat is not None
    assert len(unchanged_chat.messages) == 10  # Still the original 10 messages

    event_bus.publish.assert_not_called()


@pytest.mark.asyncio()
async def test_query_agent_handler_invalid_chat_error() -> None:
    chat_repository = InMemoryChatRepository()
    event_bus = AsyncMock(spec=EventBusService)

    user_id = uuid.uuid4()
    different_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Create a chat owned by a different user
    existing_chat = mock_chat(
        uuid=chat_id,
        user_id=different_user_id,
    )

    await chat_repository.add(existing_chat)

    handler = QueryAgentHandler(
        chat_repository=chat_repository,
        event_bus=event_bus,
    )

    query = "This should fail due to wrong user"

    with pytest.raises(InvalidChatError):
        await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    event_bus.publish.assert_not_called()


@pytest.mark.asyncio()
async def test_query_agent_handler_chat_title_truncation() -> None:
    chat_repository = InMemoryChatRepository()
    event_bus = AsyncMock(spec=EventBusService)

    handler = QueryAgentHandler(
        chat_repository=chat_repository,
        event_bus=event_bus,
    )

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    long_query = "This is a very long query that should be truncated when used as the chat title because it exceeds the maximum length"

    await handler.handle(user_id=user_id, query=long_query, chat_id=chat_id)

    # Check that chat was created with a truncated title
    created_chat = await chat_repository.get(chat_id)
    assert created_chat is not None
    assert len(created_chat.title) == 50  # 47 chars + "..."
    assert created_chat.title.endswith("...")


@pytest.mark.asyncio()
async def test_query_agent_rejects_query_if_a_previous_one_is_being_processed() -> None:
    chat_repository = InMemoryChatRepository()
    event_bus = AsyncMock(spec=EventBusService)

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Create a chat where the last message is from the user and recent
    messages = [
        mock_chat_message(role=ChatRole.USER, content="Recent query"),
    ]

    existing_chat = mock_chat(
        uuid=chat_id,
        user_id=user_id,
        messages=messages,
    )

    await chat_repository.add(existing_chat)

    handler = QueryAgentHandler(
        chat_repository=chat_repository,
        event_bus=event_bus,
    )

    query = "Another query while processing"

    with pytest.raises(MessageIsBeingProcessedError):
        await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    # Verify chat was not modified
    unchanged_chat = await chat_repository.get(chat_id)
    assert unchanged_chat is not None
    assert len(unchanged_chat.messages) == 1  # Still the original message

    event_bus.publish.assert_not_called()
