from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated, Any, Callable, Coroutine
from uuid import UUID

from fastapi import Depends, Query, Request, Response, status
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import (
    AssignSubscriptionToTopicHandler,
)
from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.topics.favorite_topic_handler import FavoriteTopicHandler
from linkurator_core.application.topics.find_topics_by_name_handler import FindTopicsByNameHandler
from linkurator_core.application.topics.follow_topic_handler import FollowTopicHandler
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.topics.unassign_subscription_from_user_topic_handler import (
    UnassignSubscriptionFromUserTopicHandler,
)
from linkurator_core.application.topics.unfavorite_topic_handler import UnfavoriteTopicHandler
from linkurator_core.application.topics.unfollow_topic_handler import UnfollowTopicHandler
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, TopicNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.default_responses import EmptyResponse
from linkurator_core.infrastructure.fastapi.models.item import VALID_INTERACTIONS, InteractionFilterSchema, ItemSchema
from linkurator_core.infrastructure.fastapi.models.page import FullPage, Page
from linkurator_core.infrastructure.fastapi.models.topic import NewTopicSchema, TopicSchema, UpdateTopicSchema


def get_router(  # pylint: disable-msg=too-many-locals disable-msg=too-many-statements
        get_session: Callable[[Request], Coroutine[Any, Any, Session | None]],
        get_user_profile_handler: GetUserProfileHandler,
        create_topic_handler: CreateTopicHandler,
        get_user_topics_handler: GetUserTopicsHandler,
        get_topic_handler: GetTopicHandler,
        get_topic_items_handler: GetTopicItemsHandler,
        find_topics_by_name_handler: FindTopicsByNameHandler,
        assign_subscription_to_user_topic_handler: AssignSubscriptionToTopicHandler,
        unassign_subscription_from_user_topic_handler: UnassignSubscriptionFromUserTopicHandler,
        delete_user_topic_handler: DeleteUserTopicHandler,
        update_user_topic_handler: UpdateTopicHandler,
        follow_topic_handler: FollowTopicHandler,
        unfollow_topic_handler: UnfollowTopicHandler,
        favorite_topic_handler: FavoriteTopicHandler,
        unfavorite_topic_handler: UnfavoriteTopicHandler,
) -> APIRouter:
    """Get the router for the topics."""
    router = APIRouter()

    @router.get("/{topic_id}/items",
                responses={
                    status.HTTP_404_NOT_FOUND: {"model": None},
                })
    async def items_by_topic(
            request: Request,
            topic_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: float | None = None,
            search: str | None = None,
            min_duration: int | None = None,
            max_duration: int | None = None,
            include_interactions: Annotated[str | None, Query(
                description=f"Comma separated values. Valid values: {VALID_INTERACTIONS}")] = None,
            excluded_subscriptions: Annotated[str | None, Query(
                description="Comma separated subscriptions UUIDs")] = None,
            session: Session | None = Depends(get_session),
    ) -> Page[ItemSchema]:
        """Get the items from a topic."""
        if created_before_ts is None:
            created_before_ts = datetime.now(timezone.utc).timestamp()

        try:
            interactions = None
            if include_interactions is not None:
                interactions = [InteractionFilterSchema(interaction) for interaction in include_interactions.split(",")]
        except ValueError as error:
            msg = "Invalid interaction filter"
            raise default_responses.bad_request(msg) from error

        def _include_interaction(interaction: InteractionFilterSchema) -> bool:
            return interactions is None or interaction in interactions

        excluded_subscriptions_uuids: set[UUID] | None = None
        if excluded_subscriptions is not None:
            excluded_subscriptions_uuids = {UUID(sub_id) for sub_id in excluded_subscriptions.split(",")}

        try:
            items = await get_topic_items_handler.handle(
                user_id=session.user_id if session is not None else None,
                topic_id=topic_id,
                created_before=datetime.fromtimestamp(created_before_ts, tz=timezone.utc),
                page_number=page_number,
                page_size=page_size,
                text_filter=search,
                min_duration=min_duration,
                max_duration=max_duration,
                include_items_without_interactions=_include_interaction(InteractionFilterSchema.WITHOUT_INTERACTIONS),
                include_recommended_items=_include_interaction(InteractionFilterSchema.RECOMMENDED),
                include_discouraged_items=_include_interaction(InteractionFilterSchema.DISCOURAGED),
                include_viewed_items=_include_interaction(InteractionFilterSchema.VIEWED),
                include_hidden_items=_include_interaction(InteractionFilterSchema.HIDDEN),
                excluded_subscriptions=excluded_subscriptions_uuids,
            )

            current_url = request.url.include_query_params(
                page_number=page_number,
                page_size=page_size,
                created_before_ts=created_before_ts,
            )

            return Page[ItemSchema].create(
                elements=[
                    ItemSchema.from_domain_item(
                        item=item.item,
                        interactions=item.interactions,
                        subscription=item.subscription)
                    for item in items
                ],
                page_number=page_number,
                page_size=page_size,
                current_url=current_url)

        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                })
    async def get_all_topics(
            request: Request,
            session: Session | None = Depends(get_session),
    ) -> Page[TopicSchema]:
        """Get all the topics from a user."""
        if session is None:
            raise default_responses.not_authenticated()

        results = await asyncio.gather(
            get_user_profile_handler.handle(session.user_id),
            get_user_topics_handler.handle(user_id=session.user_id),
        )
        user = results[0]
        response = results[1]

        return Page[TopicSchema].create(
            elements=[TopicSchema.from_domain_topic(element.topic, element.curator, user)
                      for element in response],
            page_number=0,
            page_size=len(response) + 1,
            current_url=request.url)

    @router.get("/name/{name}",
                responses={
                })
    async def find_topics_by_name(
            name: str,
            session: Session | None = Depends(get_session),
    ) -> FullPage[TopicSchema]:
        """Find topics by name."""

        async def get_user_profile(session: Session | None) -> User | None:
            if session is None:
                return None
            return await get_user_profile_handler.handle(session.user_id)

        results = await asyncio.gather(
            get_user_profile(session),
            find_topics_by_name_handler.handle(name=name),
        )
        user = results[0]
        response = results[1]
        return FullPage[TopicSchema].create(
            elements=[TopicSchema.from_domain_topic(element.topic, element.curator, user)
                      for element in response],
        )

    @router.get("/{topic_id}",
                responses={
                    status.HTTP_404_NOT_FOUND: {"model": None},
                })
    async def get_topic(
            topic_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> TopicSchema:
        """Get a topic information from a user."""

        async def get_user_profile(session: Session | None) -> User | None:
            if session is None:
                return None
            return await get_user_profile_handler.handle(session.user_id)

        try:
            results = await asyncio.gather(
                get_user_profile(session),
                get_topic_handler.handle(topic_id=topic_id),
            )
            user = results[0]
            topic = results[1].topic
            curator = results[1].curator
            return TopicSchema.from_domain_topic(topic, curator, user)
        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error

    @router.post("/",
                 status_code=status.HTTP_201_CREATED,
                 response_class=Response,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None},
                 })
    async def create_topic(
            new_topic: NewTopicSchema,
            session: Session | None = Depends(get_session),
    ) -> None:
        """Create a new topic for a user."""
        if session is None:
            raise default_responses.not_authenticated()

        await create_topic_handler.handle(Topic.new(
            uuid=new_topic.uuid,
            name=new_topic.name,
            user_id=session.user_id,
            subscription_ids=new_topic.subscriptions_ids,
        ))

    @router.patch("/{topic_id}",
                  status_code=status.HTTP_204_NO_CONTENT,
                  responses={
                      status.HTTP_401_UNAUTHORIZED: {"model": None},
                      status.HTTP_404_NOT_FOUND: {"model": None},
                  })
    async def update_topic(
            topic_id: UUID,
            topic_update: UpdateTopicSchema,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        """Update a topic."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await update_user_topic_handler.handle(
                topic_id=topic_id,
                name=topic_update.name,
                subscriptions_ids=topic_update.subscriptions_ids)
        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error
        except SubscriptionNotFoundError as error:
            msg = "Subscription not found"
            raise default_responses.not_found(msg) from error

        return EmptyResponse()

    @router.delete("/{topic_id}",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                       status.HTTP_404_NOT_FOUND: {"model": None},
                   })
    async def delete_topic(
            topic_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        """Delete a topic."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await delete_user_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)
        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error

        return EmptyResponse()

    @router.post("/{topic_id}/subscriptions/{subscription_id}",
                 status_code=status.HTTP_201_CREATED,
                 response_class=Response,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None},
                 })
    async def assign_subscription_to_topic(
            topic_id: UUID,
            subscription_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> None:
        """Assign a subscription to a topic."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await assign_subscription_to_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError as error:
            msg = "Subscription not found"
            raise default_responses.not_found(msg) from error
        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error

    @router.delete("/{topic_id}/subscriptions/{subscription_id}",
                   status_code=status.HTTP_204_NO_CONTENT,
                   response_class=Response,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                       status.HTTP_404_NOT_FOUND: {"model": None},
                   })
    async def remove_subscription_from_topic(
            topic_id: UUID,
            subscription_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        """Remove subscription from topic."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await unassign_subscription_from_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError as error:
            msg = "Subscription not found"
            raise default_responses.not_found(msg) from error
        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error

        return EmptyResponse()

    @router.post("/{topic_id}/follow",
                 status_code=status.HTTP_201_CREATED,
                 response_class=Response,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None},
                 })
    async def follow_topic(
            topic_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> None:
        """Follow a topic."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await follow_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)
        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error

    @router.delete("/{topic_id}/follow",
                   status_code=status.HTTP_204_NO_CONTENT,
                   response_class=Response,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                       status.HTTP_404_NOT_FOUND: {"model": None},
                   })
    async def unfollow_topic(
            topic_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        """Unfollow a topic."""
        if session is None:
            raise default_responses.not_authenticated()

        await unfollow_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)

        return EmptyResponse()

    @router.post("/{topic_id}/favorite",
                 status_code=status.HTTP_201_CREATED,
                 response_class=Response,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None},
                 })
    async def favorite_topic(
            topic_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> None:
        """Favorite a topic."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await favorite_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)
        except TopicNotFoundError as error:
            msg = "Topic not found"
            raise default_responses.not_found(msg) from error

    @router.delete("/{topic_id}/favorite",
                   status_code=status.HTTP_204_NO_CONTENT,
                   response_class=Response,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                   })
    async def unfavorite_topic(
            topic_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        """Unfavorite a topic."""
        if session is None:
            raise default_responses.not_authenticated()

        await unfavorite_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)

        return EmptyResponse()

    return router
