"""
Main file of the application
"""
from dataclasses import dataclass
from typing import Optional

from fastapi.applications import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from linkurator_core.application.assign_subscription_to_user_topic_handler import AssignSubscriptionToTopicHandler
from linkurator_core.application.create_topic_handler import CreateTopicHandler
from linkurator_core.application.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.get_topic_handler import GetTopicHandler
from linkurator_core.application.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.unassign_subscription_from_user_topic_handler import \
    UnassignSubscriptionFromUserTopicHandler
from linkurator_core.application.update_topic_handler import UpdateTopicHandler
from linkurator_core.application.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.session import Session
from linkurator_core.infrastructure.fastapi.routers import authentication, profile, subscriptions, topics
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


@dataclass
class Handlers:  # pylint: disable=too-many-instance-attributes
    validate_token: ValidateTokenHandler
    google_client: GoogleAccountService
    get_user_subscriptions: GetUserSubscriptionsHandler
    get_subscription_items_handler: GetSubscriptionItemsHandler
    get_user_profile_handler: GetUserProfileHandler
    create_topic_handler: CreateTopicHandler
    get_user_topics_handler: GetUserTopicsHandler
    get_topic_handler: GetTopicHandler
    assign_subscription_to_topic_handler: AssignSubscriptionToTopicHandler
    unassign_subscription_from_topic_handler: UnassignSubscriptionFromUserTopicHandler
    get_topic_items_handler: GetTopicItemsHandler
    delete_topic_handler: DeleteUserTopicHandler
    update_topic_handler: UpdateTopicHandler


def create_app_from_handlers(handlers: Handlers) -> FastAPI:
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
        authentication.get_router(
            validate_token_handler=handlers.validate_token,
            google_client=handlers.google_client))
    app.include_router(
        profile.get_router(
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler
        ),
        prefix="/profile"
    )
    app.include_router(
        topics.get_router(
            get_session=get_current_session,
            create_topic_handler=handlers.create_topic_handler,
            get_topic_items_handler=handlers.get_topic_items_handler,
            get_topic_handler=handlers.get_topic_handler,
            get_user_topics_handler=handlers.get_user_topics_handler,
            assign_subscription_to_user_topic_handler=handlers.assign_subscription_to_topic_handler,
            unassign_subscription_from_user_topic_handler=handlers.unassign_subscription_from_topic_handler,
            delete_user_topic_handler=handlers.delete_topic_handler,
            update_user_topic_handler=handlers.update_topic_handler
        ),
        prefix="/topics")
    app.include_router(
        subscriptions.get_router(
            get_session=get_current_session,
            get_user_subscriptions_handler=handlers.get_user_subscriptions,
            get_subscription_items_handler=handlers.get_subscription_items_handler),
        prefix="/subscriptions")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    return app
