from typing import Any, Callable, Coroutine, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, status

from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.items.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.application.items.get_item_handler import GetItemHandler
from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        get_item_handler: GetItemHandler,
        create_item_interaction_handler: CreateItemInteractionHandler,
        delete_item_interaction_handler: DeleteItemInteractionHandler,
) -> APIRouter:
    router = APIRouter()

    @router.post("/{item_id}/interactions/{interaction_type}",
                 status_code=status.HTTP_201_CREATED,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None},
                 })
    async def create_item_interaction(
            item_id: UUID,
            interaction_type: InteractionType,
            session: Optional[Session] = Depends(get_session),
    ) -> None:
        """Create an interaction for an item."""
        if session is None:
            raise default_responses.not_authenticated()

        await create_item_interaction_handler.handle(Interaction.new(
            uuid=uuid4(),
            user_uuid=session.user_id,
            item_uuid=item_id,
            interaction_type=interaction_type))

    @router.delete("/{item_id}/interactions/{interaction_type}",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                       status.HTTP_404_NOT_FOUND: {"model": None},
                   })
    async def delete_interaction(
            item_id: UUID,
            interaction_type: InteractionType,
            session: Optional[Session] = Depends(get_session),
    ) -> None:
        if session is None:
            raise default_responses.not_authenticated()

        await delete_item_interaction_handler.handle(session.user_id, item_id, interaction_type)

    @router.get("/{item_id}",
                status_code=status.HTTP_200_OK,
                responses={
                    status.HTTP_404_NOT_FOUND: {"model": None},
                })
    async def get_item(
            item_id: UUID,
            session: Optional[Session] = Depends(get_session),
    ) -> ItemSchema:
        """Get an item."""
        if session is None:
            raise default_responses.not_authenticated()

        try:
            response = await get_item_handler.handle(user_id=session.user_id, item_id=item_id)
            return ItemSchema.from_domain_item(
                item=response.item,
                subscription=response.subscription,
                interactions=response.interactions)
        except ItemNotFoundError as error:
            msg = "Item not found"
            raise default_responses.not_found(msg) from error

    return router
