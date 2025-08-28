from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService
from linkurator_core.domain.common.mock_factory import mock_item, mock_sub


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
