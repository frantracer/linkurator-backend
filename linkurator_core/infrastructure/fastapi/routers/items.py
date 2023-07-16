import http
from typing import Callable, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response

from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.items.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.application.items.get_item_handler import GetItemHandler
from linkurator_core.domain.items.interaction import InteractionType, Interaction
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema


def get_router(
        get_session: Callable,
        get_item_handler: GetItemHandler,
        create_item_interaction_handler: CreateItemInteractionHandler,
        delete_item_interaction_handler: DeleteItemInteractionHandler,
) -> APIRouter:
    router = APIRouter()

    @router.post("/{item_id}/interactions/{interaction_type}", response_model=None,
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

    @router.delete("/{item_id}/interactions/{interaction_type}", response_model=None,
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

    @router.get("/{item_id}", response_model=ItemSchema,
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

    return router
