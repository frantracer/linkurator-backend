from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional, Annotated
from uuid import UUID

from fastapi import Depends, Request, Response, Query, status
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import \
    AssignSubscriptionToTopicHandler
from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.topics.follow_topic_handler import FollowTopicHandler
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.topics.unassign_subscription_from_user_topic_handler import \
    UnassignSubscriptionFromUserTopicHandler
from linkurator_core.application.topics.unfollow_topic_handler import UnfollowTopicHandler
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, TopicNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema, InteractionFilterSchema, VALID_INTERACTIONS
from linkurator_core.infrastructure.fastapi.models.page import Page
from linkurator_core.infrastructure.fastapi.models.topic import NewTopicSchema, TopicSchema, UpdateTopicSchema


def get_router(  # pylint: disable-msg=too-many-locals disable-msg=too-many-statements
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        create_topic_handler: CreateTopicHandler,
        get_user_topics_handler: GetUserTopicsHandler,
        get_topic_handler: GetTopicHandler,
        get_topic_items_handler: GetTopicItemsHandler,
        assign_subscription_to_user_topic_handler: AssignSubscriptionToTopicHandler,
        unassign_subscription_from_user_topic_handler: UnassignSubscriptionFromUserTopicHandler,
        delete_user_topic_handler: DeleteUserTopicHandler,
        update_user_topic_handler: UpdateTopicHandler,
        follow_topic_handler: FollowTopicHandler,
        unfollow_topic_handler: UnfollowTopicHandler
) -> APIRouter:
    """
    Get the router for the topics
    """

    router = APIRouter()

    @router.get("/{topic_id}/items",
                responses={
                    status.HTTP_404_NOT_FOUND: {'model': None}
                })
    async def items_by_topic(
            request: Request,
            topic_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: Optional[float] = None,
            search: Optional[str] = None,
            min_duration: Optional[int] = None,
            max_duration: Optional[int] = None,
            include_interactions: Annotated[str | None, Query(
                description=f"Comma separated values. Valid values: {VALID_INTERACTIONS}")] = None,
            session: Optional[Session] = Depends(get_session)
    ) -> Page[ItemSchema]:
        """
        Get the items from a topic
        """
        if created_before_ts is None:
            created_before_ts = datetime.now(timezone.utc).timestamp()

        try:
            interactions = None
            if include_interactions is not None:
                interactions = [InteractionFilterSchema(interaction) for interaction in include_interactions.split(',')]
        except ValueError as error:
            raise default_responses.bad_request('Invalid interaction filter') from error

        def _include_interaction(interaction: InteractionFilterSchema) -> bool:
            return interactions is None or interaction in interactions

        try:
            items_with_interactions = await get_topic_items_handler.handle(
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
            )

            current_url = request.url.include_query_params(
                page_number=page_number,
                page_size=page_size,
                created_before_ts=created_before_ts
            )

            return Page[ItemSchema].create(
                elements=[ItemSchema.from_domain_item(item_with_interactions[0], item_with_interactions[1])
                          for item_with_interactions in items_with_interactions],
                page_number=page_number,
                page_size=page_size,
                current_url=current_url)

        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None}
                })
    async def get_all_topics(
            request: Request,
            session: Optional[Session] = Depends(get_session)
    ) -> Page[TopicSchema]:
        """
        Get all the topics from a user
        """
        if session is None:
            raise default_responses.not_authenticated()

        response = await get_user_topics_handler.handle(user_id=session.user_id)

        return Page[TopicSchema].create(
            elements=[TopicSchema.from_domain_topic(topic, session.user_id, topic.uuid in response.followed_topics_ids)
                      for topic
                      in response.topics],
            page_number=0,
            page_size=len(response.topics) + 1,
            current_url=request.url)

    @router.get("/{topic_id}",
                responses={
                    status.HTTP_404_NOT_FOUND: {'model': None}
                })
    async def get_topic(
            topic_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> TopicSchema:
        """
        Get a topic information from a user
        """
        user_id: Optional[UUID] = None
        if session is not None:
            user_id = session.user_id

        try:
            response = await get_topic_handler.handle(topic_id=topic_id, user_id=user_id)
            return TopicSchema.from_domain_topic(response.topic, user_id, response.followed)
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.post("/",
                 status_code=status.HTTP_201_CREATED,
                 response_class=Response,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {'model': None},
                     status.HTTP_404_NOT_FOUND: {'model': None}
                 })
    async def create_topic(
            new_topic: NewTopicSchema,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Create a new topic for a user
        """
        if session is None:
            raise default_responses.not_authenticated()

        await create_topic_handler.handle(Topic.new(
            uuid=new_topic.uuid,
            name=new_topic.name,
            user_id=session.user_id,
            subscription_ids=new_topic.subscriptions_ids
        ))
        return

    @router.patch("/{topic_id}",
                  status_code=status.HTTP_204_NO_CONTENT,
                  responses={
                      status.HTTP_401_UNAUTHORIZED: {'model': None},
                      status.HTTP_404_NOT_FOUND: {'model': None}
                  })
    async def update_topic(
            topic_id: UUID,
            topic_update: UpdateTopicSchema,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Update a topic
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await update_user_topic_handler.handle(
                topic_id=topic_id,
                name=topic_update.name,
                subscriptions_ids=topic_update.subscriptions_ids)
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found('Subscription not found') from error

    @router.delete("/{topic_id}",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {'model': None},
                       status.HTTP_404_NOT_FOUND: {'model': None}
                   })
    async def delete_topic(
            topic_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Delete a topic
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await delete_user_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.post("/{topic_id}/subscriptions/{subscription_id}",
                 status_code=status.HTTP_201_CREATED,
                 response_class=Response,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {'model': None},
                     status.HTTP_404_NOT_FOUND: {'model': None}
                 })
    async def assign_subscription_to_topic(
            topic_id: UUID,
            subscription_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Assign a subscription to a topic
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await assign_subscription_to_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found('Subscription not found') from error
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.delete("/{topic_id}/subscriptions/{subscription_id}",
                   status_code=status.HTTP_204_NO_CONTENT,
                   response_class=Response,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {'model': None},
                       status.HTTP_404_NOT_FOUND: {'model': None}
                   })
    async def remove_subscription_from_topic(
            topic_id: UUID,
            subscription_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Remove subscription from topic
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await unassign_subscription_from_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found('Subscription not found') from error
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.post("/{topic_id}/follow",
                 status_code=status.HTTP_201_CREATED,
                 response_class=Response,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {'model': None},
                     status.HTTP_404_NOT_FOUND: {'model': None}
                 })
    async def follow_topic(
            topic_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Follow a topic
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await follow_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.delete("/{topic_id}/follow",
                   status_code=status.HTTP_204_NO_CONTENT,
                   response_class=Response,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {'model': None},
                       status.HTTP_404_NOT_FOUND: {'model': None}
                   })
    async def unfollow_topic(
            topic_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Unfollow a topic
        """
        if session is None:
            raise default_responses.not_authenticated()

        await unfollow_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)

    return router
