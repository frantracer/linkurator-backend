import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Request
from pydantic import NonNegativeInt, PositiveInt

from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsHandler
from linkurator_core.application.users.find_user_handler import FindCuratorHandler
from linkurator_core.application.users.follow_curator_handler import FollowCuratorHandler
from linkurator_core.application.users.get_curators_handler import GetCuratorsHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.users.unfollow_curator_handler import UnfollowCuratorHandler
from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.user import Username
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.curator import CuratorSchema
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema
from linkurator_core.infrastructure.fastapi.models.page import Page, FullPage
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema
from linkurator_core.infrastructure.fastapi.models.topic import TopicSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        get_user_profile_handler: GetUserProfileHandler,
        find_user_handler: FindCuratorHandler,
        get_curators_handler: GetCuratorsHandler,
        follow_curator_handler: FollowCuratorHandler,
        unfollow_curator_handler: UnfollowCuratorHandler,
        get_curator_topics_handler: GetCuratorTopicsHandler,
        get_curator_subscriptions_handler: GetUserSubscriptionsHandler,
        get_curator_items_handler: GetCuratorItemsHandler
) -> APIRouter:
    router = APIRouter()

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None}
                })
    async def get_curators(
            session: Optional[Session] = Depends(get_session),
    ) -> list[CuratorSchema]:
        if session is None:
            raise default_responses.not_authenticated()

        curators = await get_curators_handler.handle(session.user_id)

        return [CuratorSchema.from_domain_user(user=curator, followed=True) for curator in curators]

    @router.post("/{curator_id}/follow",
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {'model': None},
                     status.HTTP_404_NOT_FOUND: {'model': None}
                 },
                 status_code=status.HTTP_201_CREATED)
    async def follow_curator(
            curator_id: UUID,
            session: Optional[Session] = Depends(get_session),
    ) -> None:
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await follow_curator_handler.handle(session.user_id, curator_id)
        except UserNotFoundError as exc:
            raise default_responses.not_found(str(exc))

    @router.delete("/{curator_id}/follow",
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {'model': None},
                       status.HTTP_404_NOT_FOUND: {'model': None}
                   },
                   status_code=status.HTTP_204_NO_CONTENT)
    async def unfollow_curator(
            curator_id: UUID,
            session: Optional[Session] = Depends(get_session),
    ) -> None:
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await unfollow_curator_handler.handle(session.user_id, curator_id)
        except UserNotFoundError as exc:
            raise default_responses.not_found(str(exc))

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

        try:
            response = await find_user_handler.handle(Username(username), session.user_id)
            if response.user is None:
                raise default_responses.not_found("User not found")
            return CuratorSchema.from_domain_user(user=response.user, followed=response.followed)
        except ValueError as exc:
            raise default_responses.bad_request(message=str(exc))

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

        results = await asyncio.gather(
            get_curator_topics_handler.handle(curator_id),
            get_user_profile_handler.handle(session.user_id)
        )
        response = results[0]
        user = results[1]
        return [TopicSchema.from_domain_topic(topic=topic, curator=response.curator, user=user)
                for topic in response.topics]

    @router.get("/{curator_id}/subscriptions",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None},
                    status.HTTP_404_NOT_FOUND: {'model': None}
                })
    async def find_curator_subscriptions(
            curator_id: UUID,
            session: Optional[Session] = Depends(get_session),
    ) -> FullPage[SubscriptionSchema]:
        if session is None:
            raise default_responses.not_authenticated()

        results = await asyncio.gather(
            get_curator_subscriptions_handler.handle(user_id=curator_id),
            get_user_profile_handler.handle(session.user_id)
        )
        curator_subs = results[0]
        user = results[1]

        return FullPage.create(
            [SubscriptionSchema.from_domain_subscription(sub, user)
             for sub in curator_subs])

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
            search: Optional[str] = None,
            min_duration: Optional[int] = None,
            max_duration: Optional[int] = None,
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
            text_filter=search,
            min_duration=min_duration,
            max_duration=max_duration
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
