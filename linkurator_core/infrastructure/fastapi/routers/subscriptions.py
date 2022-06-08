from datetime import datetime
import http
from typing import Any, Callable, Optional

from fastapi import Depends
from fastapi.applications import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.application.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.common import utils
from linkurator_core.domain.session import Session
from linkurator_core.infrastructure.fastapi.models.page import Page
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema


def get_router(get_session: Callable, get_user_subscriptions_handler: GetUserSubscriptionsHandler) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_model=Page[SubscriptionSchema])
    async def get_all_subscriptions(request: Request, page_number: NonNegativeInt = 0, page_size: PositiveInt = 50,
                                    created_before_ts: float = datetime.now().timestamp(),
                                    session: Optional[Session] = Depends(get_session)) -> Any:
        """
        Get the list of the user subscriptions
        """
        if session is None:
            return JSONResponse(status_code=http.HTTPStatus.UNAUTHORIZED)

        subscriptions, total_subs = get_user_subscriptions_handler.handle(
            session.user_id, page_number, page_size, datetime.fromtimestamp(created_before_ts))

        base_url = request.url.remove_query_params(["page_number", "page_size", "created_before"])
        next_page_url = None
        if page_number < total_subs // page_size:
            next_page_url = utils.parse_url(str(base_url.include_query_params(
                page_number=page_number + 1, page_size=page_size, created_before=created_before_ts)))

        previous_page_url = None
        if page_number > 0:
            previous_page_url = utils.parse_url(str(base_url.include_query_params(
                page_number=page_number - 1, page_size=page_size, created_before=created_before_ts)))

        return Page[SubscriptionSchema](
            elements=[SubscriptionSchema.from_domain_subscription(subscription) for subscription in subscriptions],
            total_elements=total_subs,
            page_number=page_number,
            page_size=page_size,
            previous_page=previous_page_url,
            next_page=next_page_url
        )

    return router
