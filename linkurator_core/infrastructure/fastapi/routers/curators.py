from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Request

from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsAsUserHandler
from linkurator_core.application.users.find_user_handler import FindUserHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.curator import CuratorSchema
from linkurator_core.infrastructure.fastapi.models.topic import TopicSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        find_user_handler: FindUserHandler,
        get_curator_topics_as_user: GetCuratorTopicsAsUserHandler
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
    ) -> CuratorSchema:
        if session is None:
            raise default_responses.not_authenticated()

        user = await find_user_handler.handle(username)
        if user is None:
            raise default_responses.not_found("User not found")
        return CuratorSchema.from_domain_user(user)

    @router.get("/{curator_id}/topics",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None},
                    status.HTTP_404_NOT_FOUND: {'model': None}
                })
    async def find_user_topics(
            curator_id: UUID,
            session: Optional[Session] = Depends(get_session),
    ) -> list[TopicSchema]:
        if session is None:
            raise default_responses.not_authenticated()

        response = await get_curator_topics_as_user.handle(curator_id, session.user_id)

        return [
            TopicSchema.from_domain_topic(
                topic=topic.topic,
                current_user_id=session.user_id,
                followed=topic.followed)
            for topic
            in response
        ]

    return router
