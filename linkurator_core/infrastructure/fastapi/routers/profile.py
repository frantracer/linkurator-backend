import http
from typing import Any, Callable, Coroutine, Optional

from fastapi import APIRouter, Depends
from fastapi.applications import Request
from fastapi.responses import JSONResponse

from linkurator_core.application.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.domain.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.profile import ProfileSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        get_user_profile_handler: GetUserProfileHandler
) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_model=ProfileSchema)
    async def get_user_profile(
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        if session is None:
            return default_responses.not_authenticated()

        user = get_user_profile_handler.handle(session.user_id)
        if user is None:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND)
        return ProfileSchema.from_domain_user(user)

    return router
