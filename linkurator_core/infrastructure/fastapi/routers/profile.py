from __future__ import annotations

from typing import Any, Callable, Coroutine

from fastapi import APIRouter, Depends, Request, status

from linkurator_core.application.users.delete_user_handler import DeleteUserHandler
from linkurator_core.application.users.edit_user_profile import EditUserProfile, NewProfileAttributes
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.default_responses import EmptyResponse
from linkurator_core.infrastructure.fastapi.models.profile import ProfileSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Session | None]],
        get_user_profile_handler: GetUserProfileHandler,
        edit_user_profile_handler: EditUserProfile,
        delete_user_handler: DeleteUserHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                    status.HTTP_404_NOT_FOUND: {"model": None},
                })
    async def get_user_profile(
            session: Session | None = Depends(get_session),
    ) -> ProfileSchema:
        if session is None:
            raise default_responses.not_authenticated()

        user = await get_user_profile_handler.handle(session.user_id)
        if user is None:
            msg = "User not found"
            raise default_responses.not_found(msg)
        return ProfileSchema.from_domain_user(user)

    @router.patch("/",
                  status_code=status.HTTP_204_NO_CONTENT,
                  responses={
                      status.HTTP_401_UNAUTHORIZED: {"model": None},
                  })
    async def edit_user_profile(
            new_attributes: NewProfileAttributes,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        if session is None:
            raise default_responses.not_authenticated()

        await edit_user_profile_handler.handle(user_id=session.user_id, new_attributes=new_attributes)
        return EmptyResponse()

    @router.delete("/",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                   })
    async def delete_user_profile(
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        if session is None:
            raise default_responses.not_authenticated()

        await delete_user_handler.handle(session)

        return EmptyResponse()

    return router
