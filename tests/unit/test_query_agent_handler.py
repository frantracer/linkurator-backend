import uuid
from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.chats.query_agent_handler import QueryAgentHandler
from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.domain.common.mock_factory import mock_item, mock_sub, mock_topic


@pytest.fixture(name="query_agent_service")
def query_agent_service_fixture() -> QueryAgentService:
    mock_service = AsyncMock(spec=QueryAgentService)
    expected_result = AgentQueryResult(
        message="Here's your answer!",
        items=[mock_item(), mock_item()],
        topics=[mock_topic()],
        subscriptions=[mock_sub(), mock_sub()],
    )
    mock_service.query.return_value = expected_result
    return mock_service


@pytest.fixture(name="chat_repository")
def chat_repository_fixture() -> ChatRepository:
    mock_repo = AsyncMock(spec=ChatRepository)
    mock_repo.get.return_value = None  # Simulating new chat creation
    return mock_repo


@pytest.mark.asyncio()
async def test_query_agent_handler(
    query_agent_service: QueryAgentService,
    chat_repository: ChatRepository,
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
