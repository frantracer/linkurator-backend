import uuid
from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.chats.query_agent_handler import QueryAgentHandler
from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService
from linkurator_core.domain.chats.chat import ChatRole
from linkurator_core.domain.common.exceptions import InvalidChatError, MessageIsBeingProcessedError, QueryRateLimitError
from linkurator_core.domain.common.mock_factory import (
    mock_chat,
    mock_chat_message,
    mock_item,
    mock_sub,
)
from linkurator_core.infrastructure.in_memory.chat_repository import InMemoryChatRepository


@pytest.fixture(name="query_agent_service")
def query_agent_service_fixture() -> AsyncMock:
    mock_service = AsyncMock(spec=QueryAgentService)
    expected_result = AgentQueryResult(
        message="Here's your answer!",
        items=[mock_item(), mock_item()],
        subscriptions=[mock_sub(), mock_sub()],
        topics_were_created=False,
    )
    mock_service.query.return_value = expected_result
    return mock_service


@pytest.fixture(name="chat_repository")
def chat_repository_fixture() -> InMemoryChatRepository:
    return InMemoryChatRepository()


@pytest.mark.asyncio()
async def test_query_agent_handler_new_chat(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
    handler = QueryAgentHandler(
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    query = "What should I watch today?"

    result = await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    assert isinstance(result, AgentQueryResult)
    assert result.message == "Here's your answer!"

    # Verify chat was created
    created_chat = await chat_repository.get(chat_id)
    assert created_chat is not None
    assert created_chat.user_id == user_id
    assert len(created_chat.messages) == 2  # User message + Assistant response
    assert created_chat.messages[0].role == ChatRole.USER
    assert created_chat.messages[0].content == query

    query_agent_service.query.assert_called_once_with(user_id, query, chat_id)


@pytest.mark.asyncio()
async def test_query_agent_handler_existing_chat_with_messages(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
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
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    query = "Third query"
    result = await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    assert isinstance(result, AgentQueryResult)
    assert result.message == "Here's your answer!"

    # Verify chat was updated with new messages
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None
    assert len(updated_chat.messages) == 6  # Original 4 + 2 new messages
    assert updated_chat.messages[-2].role == ChatRole.USER
    assert updated_chat.messages[-2].content == query
    assert updated_chat.messages[-1].role == ChatRole.ASSISTANT

    query_agent_service.query.assert_called_once_with(user_id, query, chat_id)


@pytest.mark.asyncio()
async def test_query_agent_handler_rate_limit_exactly_5_queries(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
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
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    query = "Sixth query should be blocked"

    with pytest.raises(QueryRateLimitError):
        await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    # Verify chat was not modified
    unchanged_chat = await chat_repository.get(chat_id)
    assert unchanged_chat is not None
    assert len(unchanged_chat.messages) == 10  # Still the original 10 messages

    query_agent_service.query.assert_not_called()


@pytest.mark.asyncio()
async def test_query_agent_handler_rate_limit_more_than_5_queries(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Create a chat with 7 user messages (over the limit)
    messages = []
    for i in range(7):
        messages.append(mock_chat_message(role=ChatRole.USER, content=f"Query {i + 1}"))
        messages.append(mock_chat_message(role=ChatRole.ASSISTANT, content=f"Response {i + 1}"))

    existing_chat = mock_chat(
        uuid=chat_id,
        user_id=user_id,
        messages=messages,
    )

    await chat_repository.add(existing_chat)

    handler = QueryAgentHandler(
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    query = "Eighth query should be blocked"

    with pytest.raises(QueryRateLimitError):
        await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    # Verify chat was not modified
    unchanged_chat = await chat_repository.get(chat_id)
    assert unchanged_chat is not None
    assert len(unchanged_chat.messages) == 14  # Still the original 14 messages

    query_agent_service.query.assert_not_called()


@pytest.mark.asyncio()
async def test_query_agent_handler_invalid_chat_error(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
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
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    query = "This should fail due to wrong user"

    with pytest.raises(InvalidChatError):
        await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    query_agent_service.query.assert_not_called()


@pytest.mark.asyncio()
async def test_query_agent_handler_chat_title_truncation(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
    handler = QueryAgentHandler(
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
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
async def test_query_agent_handler_chat_title_no_truncation(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
    handler = QueryAgentHandler(
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    short_query = "Short query"

    await handler.handle(user_id=user_id, query=short_query, chat_id=chat_id)

    # Check that chat was created with the full title
    created_chat = await chat_repository.get(chat_id)
    assert created_chat is not None
    assert created_chat.title == short_query


@pytest.mark.asyncio()
async def test_query_agent_handler_updates_chat_with_messages(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    existing_chat = mock_chat(
        uuid=chat_id,
        user_id=user_id,
        messages=[],
    )

    await chat_repository.add(existing_chat)

    handler = QueryAgentHandler(
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    query = "What should I watch today?"
    result = await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    assert isinstance(result, AgentQueryResult)

    # Verify chat was updated with both user and assistant messages
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None
    assert len(updated_chat.messages) == 2
    assert updated_chat.messages[0].role == ChatRole.USER
    assert updated_chat.messages[0].content == query
    assert updated_chat.messages[1].role == ChatRole.ASSISTANT
    assert updated_chat.messages[1].content == "Here's your answer!"


@pytest.mark.asyncio()
async def test_query_agent_handler_allows_up_to_5_queries(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Create a chat with 4 user messages (under the limit)
    messages = []
    for i in range(4):
        messages.append(mock_chat_message(role=ChatRole.USER, content=f"Query {i + 1}"))
        messages.append(mock_chat_message(role=ChatRole.ASSISTANT, content=f"Response {i + 1}"))

    existing_chat = mock_chat(
        uuid=chat_id,
        user_id=user_id,
        messages=messages,
    )

    await chat_repository.add(existing_chat)

    handler = QueryAgentHandler(
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    query = "Fifth query should work"
    result = await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    assert isinstance(result, AgentQueryResult)
    assert result.message == "Here's your answer!"

    # Verify chat was updated
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None
    assert len(updated_chat.messages) == 10  # Original 8 + 2 new messages

    query_agent_service.query.assert_called_once_with(user_id, query, chat_id)


@pytest.mark.asyncio()
async def test_query_agent_rejects_query_if_a_previous_one_is_being_processed(
    query_agent_service: AsyncMock,
    chat_repository: InMemoryChatRepository,
) -> None:
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
        query_agent_service=query_agent_service,
        chat_repository=chat_repository,
    )

    query = "Another query while processing"

    with pytest.raises(MessageIsBeingProcessedError):
        await handler.handle(user_id=user_id, query=query, chat_id=chat_id)

    # Verify chat was not modified
    unchanged_chat = await chat_repository.get(chat_id)
    assert unchanged_chat is not None
    assert len(unchanged_chat.messages) == 1  # Still the original message

    query_agent_service.query.assert_not_called()
