from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from linkurator_core.application.chats.delete_chat_handler import DeleteChatHandler
from linkurator_core.application.chats.get_chat_handler import GetChatHandler
from linkurator_core.application.chats.get_user_chats_handler import GetUserChatsHandler
from linkurator_core.application.chats.query_agent_handler import QueryAgentHandler
from linkurator_core.domain.common.exceptions import (
    MaxMessagePerChatError,
    MessageIsBeingProcessedError,
)
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.agent import AgentQueryRequest
from linkurator_core.infrastructure.fastapi.models.chat import (
    ChatResponse,
    GetUserChatsResponse,
)
from linkurator_core.infrastructure.rate_limiter import AnonymousUserRateLimiter


def get_router(
    get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
    query_agent_handler: QueryAgentHandler,
    get_user_chats_handler: GetUserChatsHandler,
    get_chat_handler: GetChatHandler,
    delete_chat_handler: DeleteChatHandler,
) -> APIRouter:
    router = APIRouter()
    query_ai_agent_rate_limiter = AnonymousUserRateLimiter(max_requests=5, window_minutes=60)

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
        user_id = None if session is None else session.user_id

        enriched_chat = await get_chat_handler.handle(chat_id=chat_id, user_id=user_id)
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
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"model": None},
            status.HTTP_400_BAD_REQUEST: {"model": None},
            status.HTTP_404_NOT_FOUND: {"model": None},
            status.HTTP_429_TOO_MANY_REQUESTS: {"model": None},
        },
    )
    async def query_agent_with_chat(
        chat_id: UUID,
        query_request: AgentQueryRequest,
        request: Request,
        session: Optional[Session] = Depends(get_session),
    ) -> ChatResponse:
        """Send a query to the AI agent within a specific chat context."""
        user_id = None if session is None else session.user_id

        # Get client IP for anonymous users
        if user_id is None:
            client_ip = get_client_ip(request)
            if query_ai_agent_rate_limiter.is_rate_limit_exceeded(client_ip):
                msg = "Rate limit exceeded. Please try again later."
                raise default_responses.rate_limit_exceeded(msg)

        try:
            await query_agent_handler.handle(
                user_id=user_id,
                query=query_request.query,
                chat_id=chat_id,
            )
        except (MaxMessagePerChatError, MessageIsBeingProcessedError) as e:
            raise default_responses.bad_request(str(e))

        enriched_chat = await get_chat_handler.handle(chat_id=chat_id, user_id=user_id)
        if enriched_chat is None:
            msg = "Chat not found after query submission"
            raise default_responses.not_found(msg)

        return ChatResponse.from_enriched_chat(enriched_chat=enriched_chat)

    return router


def get_client_ip(request: Request) -> str:
    """Extract the client's IP address from the request, considering possible proxy headers."""
    client_ip = request.client.host if request.client else "unknown"
    # Handle forwarded headers for reverse proxy scenarios
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    return client_ip
