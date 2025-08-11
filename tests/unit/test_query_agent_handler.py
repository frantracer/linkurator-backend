import uuid
from unittest.mock import AsyncMock

import pytest

from linkurator_core.application.agents.query_agent_handler import QueryAgentHandler
from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService


@pytest.fixture(name="query_agent_service")
def query_agent_service_fixture() -> QueryAgentService:
    return AsyncMock(spec=QueryAgentService)


@pytest.mark.asyncio
async def test_query_agent_handler(query_agent_service: QueryAgentService) -> None:
    expected_result = AgentQueryResult(
        message="Here's your answer!",
        items=[uuid.uuid4(), uuid.uuid4()],
        topics=[uuid.uuid4()],
        subscriptions=[uuid.uuid4(), uuid.uuid4()],
    )
    query_agent_service.query.return_value = expected_result
    
    handler = QueryAgentHandler(query_agent_service=query_agent_service)
    
    user_id = uuid.uuid4()
    query = "What should I watch today?"
    
    result = await handler.handle(user_id, query)
    
    assert isinstance(result, AgentQueryResult)
    assert result.message == expected_result.message
    assert result.items == expected_result.items
    assert result.topics == expected_result.topics
    assert result.subscriptions == expected_result.subscriptions
    
    query_agent_service.query.assert_called_once_with(user_id, query)