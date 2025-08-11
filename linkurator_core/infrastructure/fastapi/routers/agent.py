from typing import Any, Callable, Coroutine, Optional

from fastapi import APIRouter, Depends, Request, status

from linkurator_core.application.agents.query_agent_handler import QueryAgentHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.agent import AgentQueryRequest, AgentQueryResponse


def get_router(
    get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
    query_agent_handler: QueryAgentHandler,
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/query",
        status_code=status.HTTP_200_OK,
        response_model=AgentQueryResponse,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"model": None},
            status.HTTP_400_BAD_REQUEST: {"model": None},
        },
    )
    async def query_agent(
        request: AgentQueryRequest,
        session: Optional[Session] = Depends(get_session),
    ) -> AgentQueryResponse:
        """Send a query to the AI agent and get a response with relevant entities."""
        if session is None:
            raise default_responses.not_authenticated()

        result = await query_agent_handler.handle(
            user_id=session.user_id,
            query=request.query,
        )

        return AgentQueryResponse.from_domain(result)

    return router
