import http
from typing import Callable, Optional, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response

from linkurator_core.application.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.domain.interaction import InteractionType, Interaction
from linkurator_core.domain.session import Session


def get_router(
        get_session: Callable,
        create_item_interaction_handler: CreateItemInteractionHandler,
        delete_item_interaction_handler: DeleteItemInteractionHandler,
) -> APIRouter:
    router = APIRouter()

    @router.post("/{item_id}/interactions/{interaction_type}", response_model=None,
                 responses={201: {"model": None}, 403: {"model": None}, 404: {"model": None}})
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
                   responses={204: {"model": None}, 403: {"model": None}, 404: {"model": None}})
    async def delete_interaction(
            item_id: UUID,
            interaction_type: InteractionType,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        if session is None:
            return Response(status_code=http.HTTPStatus.UNAUTHORIZED)

        delete_item_interaction_handler.handle(session.user_id, item_id, interaction_type)

        return Response(status_code=http.HTTPStatus.NO_CONTENT)

    return router
