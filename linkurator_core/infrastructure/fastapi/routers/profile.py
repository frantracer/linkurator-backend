from typing import Any, Callable, Coroutine, Optional

from fastapi import APIRouter, Depends, status, Request

from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.profile import ProfileSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        get_user_profile_handler: GetUserProfileHandler
) -> APIRouter:
    router = APIRouter()

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None},
                    status.HTTP_404_NOT_FOUND: {'model': None}
                })
    async def get_user_profile(
            session: Optional[Session] = Depends(get_session)
    ) -> ProfileSchema:
        if session is None:
            raise default_responses.not_authenticated()

        user = get_user_profile_handler.handle(session.user_id)
        if user is None:
            raise default_responses.not_found("User not found")
        return ProfileSchema.from_domain_user(user)

    return router
