from datetime import datetime, timezone
import http
from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from fastapi import Depends, Response
from fastapi.applications import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.application.assign_subscription_to_user_topic_handler import AssignSubscriptionToTopicHandler
from linkurator_core.application.create_topic_handler import CreateTopicHandler
from linkurator_core.application.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.exceptions import SubscriptionNotFoundError, TopicNotFoundError
from linkurator_core.application.get_topic_handler import GetTopicHandler
from linkurator_core.application.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.unassign_subscription_from_user_topic_handler import \
    UnassignSubscriptionFromUserTopicHandler
from linkurator_core.domain.session import Session
from linkurator_core.domain.topic import Topic
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema
from linkurator_core.infrastructure.fastapi.models.message import Message
from linkurator_core.infrastructure.fastapi.models.page import Page
from linkurator_core.infrastructure.fastapi.models.topic import NewTopicSchema, TopicSchema


def get_router(  # pylint: disable-msg=too-many-locals
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        create_topic_handler: CreateTopicHandler,
        get_user_topics_handler: GetUserTopicsHandler,
        get_topic_handler: GetTopicHandler,
        get_topic_items_handler: GetTopicItemsHandler,
        assign_subscription_to_user_topic_handler: AssignSubscriptionToTopicHandler,
        unassign_subscription_from_user_topic_handler: UnassignSubscriptionFromUserTopicHandler,
        delete_user_topic_handler: DeleteUserTopicHandler
) -> APIRouter:
    """
    Get the router for the topics
    """

    router = APIRouter()

    @router.get("/{topic_id}/items",
                response_model=Page[ItemSchema])
    async def items_by_topic(
            request: Request,
            topic_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: float = datetime.now(timezone.utc).timestamp(),
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Get the items from a topic
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            items, total_items = get_topic_items_handler.handle(
                topic_id=topic_id,
                created_before=datetime.fromtimestamp(created_before_ts),
                page_number=page_number,
                page_size=page_size)

            current_url = request.url.include_query_params(
                page_number=page_number,
                page_size=page_size,
                created_before_ts=created_before_ts
            )

            return Page[ItemSchema].create(
                elements=[ItemSchema.from_domain_item(item) for item in items],
                total_elements=total_items,
                page_number=page_number,
                page_size=page_size,
                current_url=current_url)

        except TopicNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={'message': 'Topic not found'})

    @router.get("/",
                response_model=Page[TopicSchema])
    async def get_all_topics(
            request: Request,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Get all the topics from a user
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        topics = get_user_topics_handler.handle(user_id=session.user_id)

        return Page[TopicSchema].create(
            elements=[TopicSchema.from_domain_topic(topic) for topic in topics],
            total_elements=len(topics),
            page_number=0,
            page_size=len(topics) + 1,
            current_url=request.url)

    @router.get("/{topic_id}",
                response_model=TopicSchema)
    async def get_topic(
            topic_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Get a topic information from a user
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            topic = get_topic_handler.handle(topic_id=topic_id)
            return TopicSchema.from_domain_topic(topic)
        except TopicNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={"message": "Topic not found"})

    @router.post("/",
                 responses={404: {"model": None}})
    async def create_topic(
            new_topic: NewTopicSchema,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Create a new topic for a user
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        create_topic_handler.handle(Topic.new(
            uuid=new_topic.uuid,
            name=new_topic.name,
            user_id=session.user_id
        ))

        return Response(status_code=http.HTTPStatus.CREATED)

    @router.delete("/{topic_id}",
                   responses={404: {"model": None}})
    async def delete_topic(
            topic_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Delete a topic
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            delete_user_topic_handler.handle(user_id=session.user_id, topic_id=topic_id)
        except TopicNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={"message": "Topic not found"})

        return Response(status_code=http.HTTPStatus.NO_CONTENT)

    @router.post("/{topic_id}/subscriptions/{subscription_id}",
                 responses={404: {"model": Message}})
    async def assign_subscription_to_topic(
            topic_id: UUID,
            subscription_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Assign a subscription to a topic
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            assign_subscription_to_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={"message": "Subscription not found"})
        except TopicNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={"message": "Topic not found"})

        return Response(status_code=http.HTTPStatus.CREATED)

    @router.delete("/{topic_id}/subscriptions/{subscription_id}",
                   responses={404: {"model": None}})
    async def remove_subscription_from_topic(
            topic_id: UUID,
            subscription_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Remove subscription from topic
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            unassign_subscription_from_user_topic_handler.handle(
                topic_id=topic_id,
                subscription_id=subscription_id,
                user_id=session.user_id)
        except SubscriptionNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={"message": "Subscription not found"})
        except TopicNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={"message": "Topic not found"})

        return Response(status_code=http.HTTPStatus.NO_CONTENT)

    return router
