from __future__ import annotations

from typing import Any, Callable, Coroutine

from fastapi import APIRouter, Depends, Request, status

from linkurator_core.application.users.delete_user_filter_handler import DeleteUserFilterHandler
from linkurator_core.application.users.get_user_filter_handler import GetUserFilterHandler
from linkurator_core.application.users.upsert_user_filter_handler import UpsertUserFilterHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.default_responses import EmptyResponse
from linkurator_core.infrastructure.fastapi.models.user_filter import (
    UpsertUserFilterRequest,
    UserFilterSchema,
)


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Session | None]],
        get_user_filter_handler: GetUserFilterHandler,
        upsert_user_filter_handler: UpsertUserFilterHandler,
        delete_user_filter_handler: DeleteUserFilterHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                    status.HTTP_404_NOT_FOUND: {"model": None},
                })
    async def get_user_filter(
            session: Session | None = Depends(get_session),
    ) -> UserFilterSchema | None:
        if session is None:
            raise default_responses.not_authenticated()

        user_filter = await get_user_filter_handler.handle(session.user_id)
        if user_filter is None:
            return None
        return UserFilterSchema.from_domain(user_filter)

    @router.put("/",
                status_code=status.HTTP_204_NO_CONTENT,
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                })
    async def upsert_user_filter(
            request: UpsertUserFilterRequest,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        if session is None:
            raise default_responses.not_authenticated()

        await upsert_user_filter_handler.handle(
            user_id=session.user_id,
            text_filter=request.text_filter,
            min_duration=request.min_duration,
            max_duration=request.max_duration,
            include_items_without_interactions=request.include_items_without_interactions,
            include_recommended_items=request.include_recommended_items,
            include_discouraged_items=request.include_discouraged_items,
            include_viewed_items=request.include_viewed_items,
            include_hidden_items=request.include_hidden_items,
        )
        return EmptyResponse()

    @router.delete("/",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                   })
    async def delete_user_filter(
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        if session is None:
            raise default_responses.not_authenticated()

        await delete_user_filter_handler.handle(session.user_id)
        return EmptyResponse()

    return router
