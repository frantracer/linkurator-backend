from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated, Any, Callable, Coroutine
from urllib.parse import urljoin
from uuid import UUID

from fastapi import Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRouter
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.subscriptions.find_subscription_by_name_or_url_handler import (
    FindSubscriptionsByNameOrUrlHandler,
)
from linkurator_core.application.subscriptions.follow_subscription_handler import FollowSubscriptionHandler
from linkurator_core.application.subscriptions.get_subscription_handler import GetSubscriptionHandler
from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler
from linkurator_core.application.subscriptions.unfollow_subscription_handler import UnfollowSubscriptionHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.common.exceptions import (
    CannotUnfollowAssignedSubscriptionError,
    SubscriptionAlreadyUpdatedError,
    SubscriptionNotFoundError,
)
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.default_responses import EmptyResponse
from linkurator_core.infrastructure.fastapi.models.item import VALID_INTERACTIONS, InteractionFilterSchema, ItemSchema
from linkurator_core.infrastructure.fastapi.models.page import FullPage, Page
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema
from linkurator_core.infrastructure.google.account_service import GoogleAccountService

REDIRECT_URI_COOKIE_NAME = "redirect_uri_youtube_sync"


async def get_user_profile(session: Session | None, handler: GetUserProfileHandler) -> User | None:
    if session is None:
        return None
    return await handler.handle(session.user_id)


def get_router(  # pylint: disable=too-many-statements
        google_client: GoogleAccountService,
        get_session: Callable[[Request], Coroutine[Any, Any, Session | None]],
        get_user_profile_handler: GetUserProfileHandler,
        get_subscription_handler: GetSubscriptionHandler,
        get_user_subscriptions_handler: GetUserSubscriptionsHandler,
        find_subscriptions_by_name_or_url: FindSubscriptionsByNameOrUrlHandler,
        follow_subscription_handler: FollowSubscriptionHandler,
        unfollow_subscription_handler: UnfollowSubscriptionHandler,
        get_subscription_items_handler: GetSubscriptionItemsHandler,
        delete_subscription_items_handler: DeleteSubscriptionItemsHandler,
        refresh_subscription_handler: RefreshSubscriptionHandler,
        update_user_subscriptions_handler: UpdateUserSubscriptionsHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                })
    async def get_all_subscriptions(
            session: Session | None = Depends(get_session),
    ) -> FullPage[SubscriptionSchema]:
        """Get the list of the user subscriptions."""
        if session is None:
            raise default_responses.not_authenticated()

        results = await asyncio.gather(
            get_user_profile_handler.handle(session.user_id),
            get_user_subscriptions_handler.handle(session.user_id),
        )
        user = results[0]
        subscriptions = results[1]

        return FullPage.create([SubscriptionSchema.from_domain_subscription(subscription, user)
                                for subscription in subscriptions])

    @router.get("/search",
                status_code=status.HTTP_200_OK,
                )
    async def get_subscriptions_by_name_or_url(
            name_or_url: str,
            session: Session | None = Depends(get_session),
    ) -> FullPage[SubscriptionSchema]:
        """
        Get the subscription information by name or URL
        :param name_or_url: Name of the subscription or URL of the subscription
        :return: The list of subscriptions that contains the given name.
        """
        results = await asyncio.gather(
            find_subscriptions_by_name_or_url.handle(name_or_url),
            get_user_profile(session, get_user_profile_handler),
        )
        subs = results[0]
        user = results[1]

        return FullPage[SubscriptionSchema].create(
            elements=[SubscriptionSchema.from_domain_subscription(sub, user) for sub in subs],
        )

    @router.get("/{sub_id}",
                status_code=status.HTTP_200_OK,
                responses={
                    status.HTTP_404_NOT_FOUND: {"model": None},
                })
    async def get_subscription(
            sub_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> SubscriptionSchema:
        """
        Get the subscription information
        :param sub_id: UUID of the subscription included in the url
        :return: The subscription information. UNAUTHORIZED status code if the session is invalid.
        """
        try:
            results = await asyncio.gather(
                get_subscription_handler.handle(sub_id),
                get_user_profile(session, get_user_profile_handler),
            )
            subscription = results[0]
            user = results[1]

            return SubscriptionSchema.from_domain_subscription(subscription, user)
        except SubscriptionNotFoundError as error:
            msg = "Subscription not found"
            raise default_responses.not_found(msg) from error

    @router.post("/{sub_id}/follow",
                 status_code=status.HTTP_201_CREATED,
                 responses={
                     status.HTTP_401_UNAUTHORIZED: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None},
                 })
    async def follow_subscription(
            sub_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> None:
        """
        Follow a subscription
        :param sub_id: UUID of the subscription included in the url
        :param session: The session of the logged user
        :return: UNAUTHORIZED status code if the session is invalid.
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await follow_subscription_handler.handle(user_id=session.user_id, subscription_id=sub_id)
        except SubscriptionNotFoundError as error:
            msg = "Subscription not found"
            raise default_responses.not_found(msg) from error

    @router.delete("/{sub_id}/follow",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                   })
    async def unfollow_subscription(
            sub_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        """
        Unfollow a subscription
        :param sub_id: UUID of the subscription included in the url
        :param session: The session of the logged user
        :return: UNAUTHORIZED status code if the session is invalid.
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await unfollow_subscription_handler.handle(user_id=session.user_id, subscription_id=sub_id)
        except CannotUnfollowAssignedSubscriptionError as error:
            msg = "You can't unfollow an assigned subscription"
            raise default_responses.forbidden(msg) from error

        return EmptyResponse()

    @router.get("/{sub_id}/items",
                status_code=status.HTTP_200_OK,
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                    status.HTTP_404_NOT_FOUND: {"model": None},
                })
    async def get_subscription_items(
            request: Request,
            sub_id: UUID,
            page_number: NonNegativeInt = 0,
            page_size: PositiveInt = 50,
            created_before_ts: float | None = None,
            search: str | None = None,
            min_duration: int | None = None,
            max_duration: int | None = None,
            include_interactions: Annotated[str | None, Query(
                description=f"Comma separated values. Valid values: {VALID_INTERACTIONS}")] = None,
            session: Session | None = Depends(get_session),
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
                interactions = [InteractionFilterSchema(interaction) for interaction in include_interactions.split(",")]
        except ValueError as error:
            msg = "Invalid interaction filter"
            raise default_responses.bad_request(msg) from error

        def _include_interaction(interaction: InteractionFilterSchema) -> bool:
            return interactions is None or interaction in interactions

        response = await get_subscription_items_handler.handle(
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
            include_hidden_items=_include_interaction(InteractionFilterSchema.HIDDEN),
        )

        current_url = request.url.include_query_params(
            page_number=page_number,
            page_size=page_size,
            created_before_ts=created_before_ts,
        )

        return Page[ItemSchema].create(
            elements=[
                ItemSchema.from_domain_item(
                    item=item_with_interactions.item,
                    subscription=response.subscription,
                    interactions=item_with_interactions.interactions,
                )
                for item_with_interactions in response.items],
            page_number=page_number,
            page_size=page_size,
            current_url=current_url)

    @router.delete("/{sub_id}/items",
                   status_code=status.HTTP_204_NO_CONTENT,
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                       status.HTTP_403_FORBIDDEN: {"model": None},
                       status.HTTP_404_NOT_FOUND: {"model": None},
                   })
    async def delete_subscription_items(
            sub_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
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
            return EmptyResponse()
        except PermissionError as error:
            msg = "You don't have permissions to delete this subscription"
            raise default_responses.forbidden(msg) from error
        except SubscriptionNotFoundError as error:
            msg = "Subscription not found"
            raise default_responses.not_found(msg) from error

    @router.post("/{sub_id}/refresh",
                 status_code=status.HTTP_204_NO_CONTENT,
                 responses={
                     status.HTTP_403_FORBIDDEN: {"model": None},
                     status.HTTP_404_NOT_FOUND: {"model": None},
                     status.HTTP_429_TOO_MANY_REQUESTS: {"model": None},
                 })
    async def refresh_subscription_information(
            sub_id: UUID,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        """
        Refresh the subscription information
        :param sub_id: UUID of the subscripton included in the url
        :param session: The session of the logged user
        :return: UNAUTHORIZED status code if the session is invalid.
        """
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await refresh_subscription_handler.handle(subscription_id=sub_id)
            return EmptyResponse()
        except PermissionError as error:
            msg = "You don't have permissions to refresh this subscription"
            raise default_responses.forbidden(msg) from error
        except SubscriptionNotFoundError as error:
            msg = "Subscription not found"
            raise default_responses.not_found(msg) from error
        except SubscriptionAlreadyUpdatedError as error:
            msg = "Subscription already updated"
            raise default_responses.too_many_requests(msg) from error

    @router.get("/sync/youtube",
                status_code=status.HTTP_204_NO_CONTENT)
    async def sync_youtube_subscriptions(
        request: Request,
        redirect_uri: str | None = None,
        session: Session | None = Depends(get_session),
    ) -> RedirectResponse:
        """Sync the youtube subscriptions."""
        if session is None:
            return RedirectResponse(url=redirect_uri or "/login")

        youtube_channel_scope = "https://www.googleapis.com/auth/youtube.readonly"
        oauth_url = google_client.authorization_url(
            scopes=[youtube_channel_scope],
            redirect_uri=urljoin(str(request.base_url), "/subscriptions/sync/youtube_auth"),
        )

        response = RedirectResponse(url=oauth_url)
        response.set_cookie(REDIRECT_URI_COOKIE_NAME, redirect_uri or "/")
        return response


    @router.get("/sync/youtube_auth",
                status_code=status.HTTP_204_NO_CONTENT)
    async def sync_youtube_auth(
        request: Request,
        code: str | None = None,
        error: str | None = None,
        session: Session | None = Depends(get_session),
    ) -> RedirectResponse:
        """Sync the youtube subscriptions."""
        redirect_uri = request.cookies.get(REDIRECT_URI_COOKIE_NAME, "")

        if session is None:
            return RedirectResponse(url=redirect_uri or "/login")

        if error is None and code is not None:
            tokens = google_client.validate_code(
                code=code,
                redirect_uri=urljoin(str(request.base_url), "/subscriptions/sync/youtube_auth"))
            if tokens is not None and tokens.access_token is not None:
                await update_user_subscriptions_handler.handle(
                    user_id=session.user_id, access_token=tokens.access_token)

        response = RedirectResponse(url=redirect_uri or "/subscriptions")
        response.delete_cookie(REDIRECT_URI_COOKIE_NAME)
        return response

    return router
