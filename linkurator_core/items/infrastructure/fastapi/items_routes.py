import http
from datetime import datetime, timezone
from typing import Callable, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response
from fastapi.applications import Request
from fastapi.responses import JSONResponse
from pydantic import NonNegativeInt, PositiveInt

from linkurator_core.common.domain.exceptions import ItemNotFoundError, TopicNotFoundError
from linkurator_core.common.domain.session import Session
from linkurator_core.common.infrastructure.fastapi.page import Page
from linkurator_core.items.application.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.items.application.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.items.application.get_item_handler import GetItemHandler
from linkurator_core.items.application.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.items.domain.interaction import InteractionType, Interaction
from linkurator_core.items.infrastructure.fastapi.item_schema import ItemSchema
from linkurator_core.items.application.get_topic_items_handler import GetTopicItemsHandler


def get_router(
        get_session: Callable,
        get_item_handler: GetItemHandler,
        create_item_interaction_handler: CreateItemInteractionHandler,
        delete_item_interaction_handler: DeleteItemInteractionHandler,
        get_topic_items_handler: GetTopicItemsHandler,
        get_subscription_items_handler: GetSubscriptionItemsHandler,
) -> APIRouter:
    router = APIRouter()

    @router.post("/items/{item_id}/interactions/{interaction_type}", response_model=None,
                 responses={201: {"model": None}, 401: {"model": None}, 404: {"model": None}})
    async def create_item_interaction(
            item_id: UUID,
            interaction_type: InteractionType,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Create an interaction for an item
        """
        if session is None:
            return Response(status_code=http.HTTPStatus.UNAUTHORIZED)

        create_item_interaction_handler.handle(Interaction.new(
            uuid=uuid4(),
            user_uuid=session.user_id,
            item_uuid=item_id,
            interaction_type=interaction_type))
        return Response(status_code=http.HTTPStatus.CREATED)

    @router.delete("/items/{item_id}/interactions/{interaction_type}", response_model=None,
                   responses={204: {"model": None}, 401: {"model": None}, 404: {"model": None}})
    async def delete_interaction(
            item_id: UUID,
            interaction_type: InteractionType,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        if session is None:
            return Response(status_code=http.HTTPStatus.UNAUTHORIZED)

        delete_item_interaction_handler.handle(session.user_id, item_id, interaction_type)

        return Response(status_code=http.HTTPStatus.NO_CONTENT)

    @router.get("/items/{item_id}", response_model=ItemSchema,
                responses={200: {"model": ItemSchema}, 404: {"model": None}})
    async def get_item(
            item_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Get an item
        """
        if session is None:
            return Response(status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            item_detail = get_item_handler.handle(user_id=session.user_id, item_id=item_id)
            return ItemSchema.from_domain_item(item_detail.item, item_detail.interactions)
        except ItemNotFoundError:
            return Response(status_code=http.HTTPStatus.NOT_FOUND)

    @router.get("/topics/{topic_id}/items",
                response_model=Page[ItemSchema])
    async def items_by_topic(
            request: Request,
            topic_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: Optional[float] = None,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Get the items from a topic
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        if created_before_ts is None:
            created_before_ts = datetime.now(timezone.utc).timestamp()

        try:
            items_with_interactions, total_items = get_topic_items_handler.handle(
                user_id=session.user_id,
                topic_id=topic_id,
                created_before=datetime.fromtimestamp(created_before_ts, tz=timezone.utc),
                page_number=page_number,
                page_size=page_size)

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

        except TopicNotFoundError:
            return JSONResponse(status_code=http.HTTPStatus.NOT_FOUND, content={'message': 'Topic not found'})

    @router.get("/subscriptions/{sub_id}/items", response_model=Page[ItemSchema])
    async def get_subscription_items(
            request: Request,
            sub_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: Optional[float] = None,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Get the list of subscription items sorted by published date. Newer items the first ones.
        :param request: HTTP request
        :param sub_id: UUID of the subscripton included in the url
        :param page_number: Number of the page to retrieve starting at 0 (query parameters)
        :param page_size: Number of elements per page (query paramenter)
        :param created_before_ts: Filter elements created before the timestamp (query paramenter)
        :param session: The session of the logged user
        :return: A page with the items. UNAUTHORIZED status code if the session is invalid.
        """

        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        if created_before_ts is None:
            created_before_ts = datetime.now(tz=timezone.utc).timestamp()

        items_with_interactions, total_items = get_subscription_items_handler.handle(
            user_id=session.user_id,
            subscription_id=sub_id,
            created_before=datetime.fromtimestamp(created_before_ts, tz=timezone.utc),
            page_number=page_number,
            page_size=page_size)

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

    return router
