import http
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import Depends, Response
from fastapi.applications import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.common.domain.exceptions import SubscriptionNotFoundError
from linkurator_core.common.domain.session import Session
from linkurator_core.common.infrastructure.fastapi.page import Page
from linkurator_core.subscriptions.application.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.subscriptions.application.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.subscriptions.infrastructure.fastapi.subscription_schema import SubscriptionSchema


def get_router(
        get_session: Callable,
        get_user_subscriptions_handler: GetUserSubscriptionsHandler,
        delete_subscription_items_handler: DeleteSubscriptionItemsHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get("/subscriptions", response_model=Page[SubscriptionSchema])
    async def get_all_subscriptions(
            request: Request,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: Optional[float] = None,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Get the list of the user subscriptions
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        if created_before_ts is None:
            created_before_ts = datetime.now(tz=timezone.utc).timestamp()

        subscriptions, total_subs = get_user_subscriptions_handler.handle(
            session.user_id, page_number, page_size, datetime.fromtimestamp(created_before_ts, tz=timezone.utc))

        current_url = request.url.include_query_params(
            page_number=page_number,
            page_size=page_size,
            created_before_ts=created_before_ts
        )

        return Page[SubscriptionSchema].create(
            elements=[SubscriptionSchema.from_domain_subscription(subscription) for subscription in subscriptions],
            total_elements=total_subs,
            page_number=page_number,
            page_size=page_size,
            current_url=current_url)

    @router.delete("/subscriptions/{sub_id}/items", response_model=None,
                   responses={204: {"model": None}, 403: {"model": None}, 404: {"model": None}})
    async def delete_subscription_items(
            sub_id: UUID,
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        """
        Delete all the items of a subscription
        :param sub_id: UUID of the subscripton included in the url
        :param session: The session of the logged user
        :return: UNAUTHORIZED status code if the session is invalid.
        """

        if session is None:
            return Response(status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            delete_subscription_items_handler.handle(user_id=session.user_id, subscription_id=sub_id)
            return Response(status_code=http.HTTPStatus.NO_CONTENT)
        except PermissionError:
            return Response(status_code=http.HTTPStatus.FORBIDDEN)
        except SubscriptionNotFoundError:
            return Response(status_code=http.HTTPStatus.NOT_FOUND)

    return router
