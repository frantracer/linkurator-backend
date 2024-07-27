from typing import Any, Callable, Coroutine, Optional

from fastapi import APIRouter, Depends, status, Request

from linkurator_core.application.users.find_user_handler import FindUserHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.user import UserSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        find_user_handler: FindUserHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get("/username/{username}",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None},
                    status.HTTP_404_NOT_FOUND: {'model': None}
                })
    async def find_user_by_username(
            username: str,
            session: Optional[Session] = Depends(get_session),
    ) -> UserSchema:
        if session is None:
            raise default_responses.not_authenticated()

        user = await find_user_handler.handle(username)
        if user is None:
            raise default_responses.not_found("User not found")
        return UserSchema.from_domain_user(user)

    return router
