"""
Main file of the application
"""
from dataclasses import dataclass
from typing import Optional

from fastapi.applications import FastAPI, Request

from linkurator_core.application.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.session import Session
from linkurator_core.infrastructure.fastapi.routers import authentication, profile, subscriptions, topics
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


@dataclass
class Handlers:
    validate_token: ValidateTokenHandler
    google_client: GoogleAccountService
    get_user_subscriptions: GetUserSubscriptionsHandler
    get_subscription_items_handler: GetSubscriptionItemsHandler
    get_user_profile_handler: GetUserProfileHandler


def create_app(handlers: Handlers) -> FastAPI:
    app = FastAPI()

    async def get_current_session(request: Request) -> Optional[Session]:
        token = request.cookies.get("token")
        if token is None:
            return None
        session = handlers.validate_token.handle(access_token=token, refresh_token=None)
        return session

    @app.get("/health")
    async def health() -> str:
        """
        Health endpoint returns a 200 if the service is alive
        """
        return "OK"

    app.include_router(
        profile.get_router(
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler
        ),
        prefix="/profile"
    )
    app.include_router(
        authentication.get_router(
            validate_token_handler=handlers.validate_token,
            google_client=handlers.google_client))
    app.include_router(topics.get_router(), prefix="/topics")
    app.include_router(
        subscriptions.get_router(
            get_session=get_current_session,
            get_user_subscriptions_handler=handlers.get_user_subscriptions,
            get_subscription_items_handler=handlers.get_subscription_items_handler),
        prefix="/subscriptions")

    return app
