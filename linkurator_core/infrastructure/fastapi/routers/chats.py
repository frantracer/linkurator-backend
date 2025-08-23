from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from linkurator_core.application.chats.delete_chat_handler import DeleteChatHandler
from linkurator_core.application.chats.get_chat_handler import GetChatHandler
from linkurator_core.application.chats.get_user_chats_handler import GetUserChatsHandler
from linkurator_core.application.chats.query_agent_handler import QueryAgentHandler
from linkurator_core.domain.common.exceptions import MessageIsBeingProcessedError, QueryRateLimitError
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.agent import AgentQueryRequest, AgentQueryResponse
from linkurator_core.infrastructure.fastapi.models.chat import (
    ChatResponse,
    GetUserChatsResponse,
)


def get_router(
    get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
    query_agent_handler: QueryAgentHandler,
    get_user_chats_handler: GetUserChatsHandler,
    get_chat_handler: GetChatHandler,
    delete_chat_handler: DeleteChatHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "",
        status_code=status.HTTP_200_OK,
        response_model=GetUserChatsResponse,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"model": None},
        },
    )
    async def get_user_chats(
        session: Optional[Session] = Depends(get_session),
    ) -> GetUserChatsResponse:
        """Get all chats for the authenticated user."""
        if session is None:
            raise default_responses.not_authenticated()

        chats = await get_user_chats_handler.handle(user_id=session.user_id)
        return GetUserChatsResponse.from_domain(chats)

    @router.get(
        "/{chat_id}",
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"model": None},
            status.HTTP_404_NOT_FOUND: {"model": None},
        },
    )
    async def get_chat(
        chat_id: UUID,
        session: Optional[Session] = Depends(get_session),
    ) -> ChatResponse:
        """Get a specific chat with all its messages."""
        if session is None:
            raise default_responses.not_authenticated()

        enriched_chat = await get_chat_handler.handle(chat_id=chat_id, user_id=session.user_id)
        if enriched_chat is None:
            msg = "Chat not found"
            raise default_responses.not_found(msg)

        return ChatResponse.from_enriched_chat(enriched_chat=enriched_chat)

    @router.delete(
        "/{chat_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"model": None},
            status.HTTP_404_NOT_FOUND: {"model": None},
        },
    )
    async def delete_chat(
        chat_id: UUID,
        session: Optional[Session] = Depends(get_session),
    ) -> None:
        """Delete a specific chat conversation."""
        if session is None:
            raise default_responses.not_authenticated()

        success = await delete_chat_handler.handle(chat_id=chat_id, user_id=session.user_id)
        if not success:
            msg = "Chat not found"
            raise default_responses.not_found(msg)

    @router.post(
        "/{chat_id}/messages",
        status_code=status.HTTP_200_OK,
        response_model=AgentQueryResponse,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"model": None},
            status.HTTP_400_BAD_REQUEST: {"model": None},
            status.HTTP_404_NOT_FOUND: {"model": None},
            status.HTTP_429_TOO_MANY_REQUESTS: {"model": None},
        },
    )
    async def query_agent_with_chat(
        chat_id: UUID,
        request: AgentQueryRequest,
        session: Optional[Session] = Depends(get_session),
    ) -> AgentQueryResponse:
        """Send a query to the AI agent within a specific chat context."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            result = await query_agent_handler.handle(
                user_id=session.user_id,
                query=request.query,
                chat_id=chat_id,
            )
        except QueryRateLimitError as e:
            raise default_responses.rate_limit_exceeded(str(e))
        except MessageIsBeingProcessedError as e:
            raise default_responses.bad_request(str(e))

        return AgentQueryResponse.from_domain(result)

    return router
