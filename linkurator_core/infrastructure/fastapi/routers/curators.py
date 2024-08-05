from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Request
from pydantic import NonNegativeInt, PositiveInt

from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsAsUserHandler
from linkurator_core.application.users.find_user_handler import FindUserHandler
from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.curator import CuratorSchema
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema
from linkurator_core.infrastructure.fastapi.models.page import Page
from linkurator_core.infrastructure.fastapi.models.topic import TopicSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        find_user_handler: FindUserHandler,
        get_curator_topics_as_user: GetCuratorTopicsAsUserHandler,
        get_curator_items_handler: GetCuratorItemsHandler
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

    @router.get("/{curator_id}/items",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None},
                    status.HTTP_404_NOT_FOUND: {'model': None}
                })
    async def find_curator_items(
            request: Request,
            curator_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: Optional[float] = None,
            session: Optional[Session] = Depends(get_session),
    ) -> Page[ItemSchema]:
        if session is None:
            raise default_responses.not_authenticated()

        if created_before_ts is None:
            created_before_ts = datetime.now(tz=timezone.utc).timestamp()

        response = await get_curator_items_handler.handle(
            user_id=session.user_id,
            curator_id=curator_id,
            created_before=datetime.fromtimestamp(created_before_ts, tz=timezone.utc),
            page_size=page_size,
            page_number=page_number,
            curator_interactions=[InteractionType.RECOMMENDED]
        )

        current_url = request.url.include_query_params(
            page_number=page_number,
            page_size=page_size,
            created_before_ts=created_before_ts
        )

        return Page[ItemSchema].create(
            elements=[ItemSchema.from_domain_item(item.item, item.user_interactions)
                      for item in response],
            page_number=page_number,
            page_size=page_size,
            current_url=current_url)

    return router
