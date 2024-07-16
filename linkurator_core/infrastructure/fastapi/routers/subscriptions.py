from datetime import datetime, timezone
from typing import Any, Callable, Optional, Coroutine, Annotated
from uuid import UUID

from fastapi import Depends, Request, status, Query
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.subscriptions.get_subscription_handler import GetSubscriptionHandler
from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.item import ItemSchema, InteractionFilterSchema, VALID_INTERACTIONS
from linkurator_core.infrastructure.fastapi.models.page import Page
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        get_subscription_handler: GetSubscriptionHandler,
        get_user_subscriptions_handler: GetUserSubscriptionsHandler,
        get_subscription_items_handler: GetSubscriptionItemsHandler,
        delete_subscription_items_handler: DeleteSubscriptionItemsHandler,
        refresh_subscription_handler: RefreshSubscriptionHandler
) -> APIRouter:
    router = APIRouter()

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {'model': None}
                })
    async def get_all_subscriptions(
            request: Request,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: Optional[float] = None,
            session: Optional[Session] = Depends(get_session)
    ) -> Page[SubscriptionSchema]:
        """
        Get the list of the user subscriptions
        """
        if session is None:
            raise default_responses.not_authenticated()

        if created_before_ts is None:
            created_before_ts = datetime.now(tz=timezone.utc).timestamp()

        subscriptions = await get_user_subscriptions_handler.handle(
            session.user_id, page_number, page_size, datetime.fromtimestamp(created_before_ts, tz=timezone.utc))

        current_url = request.url.include_query_params(
            page_number=page_number,
            page_size=page_size,
            created_before_ts=created_before_ts
        )

        return Page[SubscriptionSchema].create(
            elements=[SubscriptionSchema.from_domain_subscription(subscription) for subscription in subscriptions],
            page_number=page_number,
            page_size=page_size,
            current_url=current_url)

    @router.get("/{sub_id}",
                status_code=status.HTTP_200_OK,
                responses={
                    status.HTTP_404_NOT_FOUND: {"model": None}
                })
    async def get_subscription(
            sub_id: UUID,
    ) -> SubscriptionSchema:
        """
        Get the subscription information
        :param sub_id: UUID of the subscription included in the url
        :return: The subscription information. UNAUTHORIZED status code if the session is invalid.
        """
        try:
            subscription = await get_subscription_handler.handle(sub_id)
            return SubscriptionSchema.from_domain_subscription(subscription)
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found("Subscription not found") from error

    @router.get("/{sub_id}/items",
                status_code=status.HTTP_200_OK,
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                    status.HTTP_404_NOT_FOUND: {"model": None}
                })
    async def get_subscription_items(
            request: Request,
            sub_id: UUID,
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
        Get the list of subscription items sorted by published date. Newer items the first ones.
        :param request: HTTP request
        :param sub_id: UUID of the subscription included in the url
        :param page_number: Number of the page to retrieve starting at 0 (query parameters)
        :param page_size: Number of elements per page (query parameter)
        :param created_before_ts: Filter elements created before the timestamp (query parameter)
        :param search: Filter elements by text (query parameter)
        :param min_duration: Filter elements with a duration greater than this value (query parameter)
        :param max_duration: Filter elements with a duration lower than this value (query parameter)
        :param include_interactions: Filter elements by interactions (query parameter)
        :param session: The session of the logged user
        :return: A page with the items. UNAUTHORIZED status code if the session is invalid.
        """

        if created_before_ts is None:
            created_before_ts = datetime.now(tz=timezone.utc).timestamp()

        try:
            interactions = None
            if include_interactions is not None:
                interactions = [InteractionFilterSchema(interaction) for interaction in include_interactions.split(',')]
        except ValueError as error:
            raise default_responses.bad_request('Invalid interaction filter') from error

        def _include_interaction(interaction: InteractionFilterSchema) -> bool:
            return interactions is None or interaction in interactions

        items_with_interactions = await get_subscription_items_handler.handle(
            user_id=session.user_id if session else None,
            subscription_id=sub_id,
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
            include_hidden_items=_include_interaction(InteractionFilterSchema.HIDDEN)
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

    @router.delete("/{sub_id}/items",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                       status.HTTP_403_FORBIDDEN: {"model": None},
                       status.HTTP_404_NOT_FOUND: {"model": None}
                   })
    async def delete_subscription_items(
            sub_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Delete all the items of a subscription
        :param sub_id: UUID of the subscription included in the url
        :param session: The session of the logged user
        :return: UNAUTHORIZED status code if the session is invalid.
        """

        if session is None:
            raise default_responses.not_authenticated()

        try:
            await delete_subscription_items_handler.handle(user_id=session.user_id, subscription_id=sub_id)
            return
        except PermissionError as error:
            raise default_responses.forbidden("You don't have permissions to delete this subscription") from error
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found("Subscription not found") from error

    @router.post("/{sub_id}/refresh",
                 status_code=status.HTTP_204_NO_CONTENT,
                 responses={
                     status.HTTP_403_FORBIDDEN: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None}
                 })
    async def refresh_subscription_information(
            sub_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> None:
        """
        Refresh the subscription information
        :param sub_id: UUID of the subscripton included in the url
        :param session: The session of the logged user
        :return: UNAUTHORIZED status code if the session is invalid.
        """

        if session is None:
            raise default_responses.not_authenticated()

        try:
            await refresh_subscription_handler.handle(user_id=session.user_id, subscription_id=sub_id)
            return
        except PermissionError as error:
            raise default_responses.forbidden("You don't have permissions to refresh this subscription") from error
        except SubscriptionNotFoundError as error:
            raise default_responses.not_found("Subscription not found") from error

    return router
