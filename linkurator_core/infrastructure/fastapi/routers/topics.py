from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from fastapi import Depends, Request, Response
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import \
    AssignSubscriptionToTopicHandler
from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.topics.unassign_subscription_from_user_topic_handler import \
    UnassignSubscriptionFromUserTopicHandler
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, TopicNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema
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
        update_user_topic_handler: UpdateTopicHandler
) -> APIRouter:
    """
    Get the router for the topics
    """

    router = APIRouter()

    @router.get("/{topic_id}/items",
                responses={
                    HTTPStatus.UNAUTHORIZED.value: {'model': None},
                    HTTPStatus.NOT_FOUND.value: {'model': None}
                })
    async def items_by_topic(
            request: Request,
            topic_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: Optional[float] = None,
            search: Optional[str] = None,
            session: Optional[Session] = Depends(get_session)
    ) -> Page[ItemSchema]:
        """
        Get the items from a topic
        """
        if session is None:
            raise default_responses.not_authenticated()

        if created_before_ts is None:
            created_before_ts = datetime.now(timezone.utc).timestamp()

        try:
            items_with_interactions, total_items = get_topic_items_handler.handle(
                user_id=session.user_id,
                topic_id=topic_id,
                created_before=datetime.fromtimestamp(created_before_ts, tz=timezone.utc),
                page_number=page_number,
                page_size=page_size,
                text_filter=search
            )

            current_url = request.url.include_query_params(
                page_number=page_number,
                page_size=page_size,
                created_before_ts=created_before_ts
            )

            return Page[ItemSchema].create(
                elements=[ItemSchema.from_domain_item(item_with_interactions[0], item_with_interactions[1])
                          for item_with_interactions in items_with_interactions],
                total_elements=total_items,
                page_number=page_number,
                page_size=page_size,
                current_url=current_url)

        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.get("/",
                responses={
                    HTTPStatus.UNAUTHORIZED: {'model': None}
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

        topics = get_user_topics_handler.handle(user_id=session.user_id)

        return Page[TopicSchema].create(
            elements=[TopicSchema.from_domain_topic(topic) for topic in topics],
            total_elements=len(topics),
            page_number=0,
            page_size=len(topics) + 1,
            current_url=request.url)

    @router.get("/{topic_id}",
                responses={
                    HTTPStatus.UNAUTHORIZED: {'model': None},
                    HTTPStatus.NOT_FOUND: {'model': None}
                })
    async def get_topic(
            topic_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> TopicSchema:
        """
        Get a topic information from a user
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            topic = get_topic_handler.handle(topic_id=topic_id)
            return TopicSchema.from_domain_topic(topic)
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.post("/",
                 status_code=HTTPStatus.CREATED,
                 response_class=Response,
                 responses={
                     HTTPStatus.NOT_FOUND: {"model": None},
                     HTTPStatus.UNAUTHORIZED: {"model": None},
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

        create_topic_handler.handle(Topic.new(
            uuid=new_topic.uuid,
            name=new_topic.name,
            user_id=session.user_id,
            subscription_ids=new_topic.subscriptions_ids
        ))

    @router.patch("/{topic_id}",
                  status_code=HTTPStatus.NO_CONTENT,
                  response_class=Response,
                  responses={
                      HTTPStatus.UNAUTHORIZED: {"model": None},
                      HTTPStatus.NOT_FOUND: {"model": None}
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
            update_user_topic_handler.handle(
                topic_id=topic_id,
                name=topic_update.name,
                subscriptions_ids=topic_update.subscriptions_ids)
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found('Subscription not found') from error

    @router.delete("/{topic_id}",
                   status_code=HTTPStatus.NO_CONTENT,
                   response_class=Response,
                   responses={
                       HTTPStatus.NOT_FOUND: {"model": None},
                       HTTPStatus.UNAUTHORIZED: {"model": None},
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
            delete_user_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.post("/{topic_id}/subscriptions/{subscription_id}",
                 status_code=HTTPStatus.CREATED,
                 response_class=Response,
                 responses={
                     HTTPStatus.UNAUTHORIZED: {"model": None},
                     HTTPStatus.NOT_FOUND: {"model": None}
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
            assign_subscription_to_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found('Subscription not found') from error
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    @router.delete("/{topic_id}/subscriptions/{subscription_id}",
                   status_code=HTTPStatus.NO_CONTENT,
                   response_class=Response,
                   responses={
                       HTTPStatus.UNAUTHORIZED: {"model": None},
                       HTTPStatus.NOT_FOUND: {"model": None}
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
            unassign_subscription_from_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found('Subscription not found') from error
        except TopicNotFoundError as error:
            raise default_responses.not_found('Topic not found') from error

    return router
