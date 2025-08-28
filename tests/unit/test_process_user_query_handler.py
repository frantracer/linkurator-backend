import uuid
from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.chats.process_user_query_handler import ProcessUserQueryHandler
from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService
from linkurator_core.domain.chats.chat import ChatRole
from linkurator_core.domain.common.mock_factory import mock_chat, mock_item, mock_sub
from linkurator_core.infrastructure.in_memory.chat_repository import InMemoryChatRepository


@pytest.mark.asyncio()
async def test_handle_successful_query() -> None:
    # Create dependencies directly
    chat_repository = InMemoryChatRepository()
    query_agent_service = AsyncMock(spec=QueryAgentService)
    chat_id = uuid.uuid4()
    user_id = uuid.uuid4()
    user_query = "Find me some programming videos"

    # Setup chat in repository
    mock_chat_obj = mock_chat(uuid=chat_id, user_id=user_id)
    await chat_repository.add(mock_chat_obj)

    # Setup mock query agent response
    mock_items = [mock_item(), mock_item()]
    mock_subscriptions = [mock_sub(), mock_sub()]
    mock_response = AgentQueryResult(
        message="Here are some programming videos!",
        items=mock_items,
        subscriptions=mock_subscriptions,
        topics_were_created=True,
    )
    query_agent_service.query.return_value = mock_response

    handler = ProcessUserQueryHandler(
        chat_repository=chat_repository,
        query_agent_service=query_agent_service,
    )

    await handler.handle(chat_id=chat_id, user_query=user_query)

    # Verify query agent service interaction
    query_agent_service.query.assert_called_once_with(
        user_id=user_id,
        chat_id=chat_id,
        query=user_query,
    )

    # Retrieve updated chat from repository
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None

    # Verify assistant message was added to chat
    assert len(updated_chat.messages) == 1
    assistant_message = updated_chat.messages[0]
    assert assistant_message.role == ChatRole.ASSISTANT
    assert assistant_message.content == "Here are some programming videos!"
    assert assistant_message.item_uuids == [item.uuid for item in mock_items]
    assert assistant_message.subscription_uuids == [sub.uuid for sub in mock_subscriptions]
    assert assistant_message.topic_were_created is True


@pytest.mark.asyncio()
async def test_handle_chat_not_found() -> None:
    # Create dependencies directly
    chat_repository = InMemoryChatRepository()
    query_agent_service = AsyncMock(spec=QueryAgentService)
    chat_id = uuid.uuid4()
    user_query = "Find me some programming videos"

    # Don't add any chat to repository (chat not found scenario)

    handler = ProcessUserQueryHandler(
        chat_repository=chat_repository,
        query_agent_service=query_agent_service,
    )

    await handler.handle(chat_id=chat_id, user_query=user_query)

    # Verify no query agent service call happened
    query_agent_service.query.assert_not_called()

    # Verify chat is still not found
    chat = await chat_repository.get(chat_id)
    assert chat is None


@pytest.mark.asyncio()
async def test_handle_query_agent_service_exception() -> None:
    # Create dependencies directly
    chat_repository = InMemoryChatRepository()
    query_agent_service = AsyncMock(spec=QueryAgentService)
    chat_id = uuid.uuid4()
    user_id = uuid.uuid4()
    user_query = "Find me some programming videos"
    error_message = "API rate limit exceeded"

    # Setup chat in repository
    mock_chat_obj = mock_chat(uuid=chat_id, user_id=user_id)
    await chat_repository.add(mock_chat_obj)

    # Setup query agent service to raise exception
    query_agent_service.query.side_effect = Exception(error_message)

    handler = ProcessUserQueryHandler(
        chat_repository=chat_repository,
        query_agent_service=query_agent_service,
    )

    await handler.handle(chat_id=chat_id, user_query=user_query)

    # Verify query agent service was called
    query_agent_service.query.assert_called_once_with(
        user_id=user_id,
        chat_id=chat_id,
        query=user_query,
    )

    # Retrieve updated chat from repository
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None

    # Verify error message was added to chat
    assert len(updated_chat.messages) == 1
    error_message_obj = updated_chat.messages[0]
    assert error_message_obj.role == ChatRole.ERROR
    assert error_message_obj.content == error_message


@pytest.mark.asyncio()
async def test_handle_empty_query_response() -> None:
    # Create dependencies directly
    chat_repository = InMemoryChatRepository()
    query_agent_service = AsyncMock(spec=QueryAgentService)
    chat_id = uuid.uuid4()
    user_id = uuid.uuid4()
    user_query = "Find me some videos"

    # Setup chat in repository
    mock_chat_obj = mock_chat(uuid=chat_id, user_id=user_id)
    await chat_repository.add(mock_chat_obj)

    # Setup mock query agent response with empty results
    mock_response = AgentQueryResult(
        message="I couldn't find any relevant content.",
        items=[],
        subscriptions=[],
        topics_were_created=False,
    )
    query_agent_service.query.return_value = mock_response

    handler = ProcessUserQueryHandler(
        chat_repository=chat_repository,
        query_agent_service=query_agent_service,
    )

    await handler.handle(chat_id=chat_id, user_query=user_query)

    # Retrieve updated chat from repository
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None

    # Verify assistant message was added with empty lists
    assert len(updated_chat.messages) == 1
    assistant_message = updated_chat.messages[0]
    assert assistant_message.role == ChatRole.ASSISTANT
    assert assistant_message.content == "I couldn't find any relevant content."
    assert assistant_message.item_uuids == []
    assert assistant_message.subscription_uuids == []
    assert assistant_message.topic_were_created is False


@pytest.mark.asyncio()
async def test_handle_query_with_existing_messages() -> None:
    # Create dependencies directly
    chat_repository = InMemoryChatRepository()
    query_agent_service = AsyncMock(spec=QueryAgentService)
    chat_id = uuid.uuid4()
    user_id = uuid.uuid4()
    user_query = "Find more videos"

    # Setup chat with existing messages
    mock_chat_obj = mock_chat(uuid=chat_id, user_id=user_id)
    mock_chat_obj.add_user_message("Previous user message")
    mock_chat_obj.add_assistant_message("Previous assistant response")
    initial_message_count = len(mock_chat_obj.messages)

    await chat_repository.add(mock_chat_obj)

    # Setup mock query agent response
    mock_response = AgentQueryResult(
        message="Here are more videos!",
        items=[mock_item()],
        subscriptions=[mock_sub()],
        topics_were_created=False,
    )
    query_agent_service.query.return_value = mock_response

    handler = ProcessUserQueryHandler(
        chat_repository=chat_repository,
        query_agent_service=query_agent_service,
    )

    await handler.handle(chat_id=chat_id, user_query=user_query)

    # Retrieve updated chat from repository
    updated_chat = await chat_repository.get(chat_id)
    assert updated_chat is not None

    # Verify new message was added to existing messages
    assert len(updated_chat.messages) == initial_message_count + 1

    # Verify the new message is correct
    new_message = updated_chat.messages[-1]
    assert new_message.role == ChatRole.ASSISTANT
    assert new_message.content == "Here are more videos!"
