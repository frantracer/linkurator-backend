from uuid import UUID

from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService


class QueryAgentHandler:
    def __init__(self, query_agent_service: QueryAgentService) -> None:
        self.query_agent_service = query_agent_service

    async def handle(self, user_id: UUID, query: str) -> AgentQueryResult:
        return await self.query_agent_service.query(user_id, query)
