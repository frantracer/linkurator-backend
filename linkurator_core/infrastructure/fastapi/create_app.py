"""
Main file of the application
"""
from dataclasses import dataclass
from typing import Optional

from fastapi.applications import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.items.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.application.items.get_item_handler import GetItemHandler
from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import \
    AssignSubscriptionToTopicHandler
from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.topics.unassign_subscription_from_user_topic_handler import \
    UnassignSubscriptionFromUserTopicHandler
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.application.users.add_external_credentials import AddExternalCredentialsHandler
from linkurator_core.application.users.delete_external_credential import DeleteExternalCredentialHandler
from linkurator_core.application.users.get_user_external_credentials import GetUserExternalCredentialsHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.users.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.routers import authentication, profile, subscriptions, topics, items, \
    credentials
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


@dataclass
class Handlers:  # pylint: disable=too-many-instance-attributes
    validate_token: ValidateTokenHandler
    google_client: GoogleAccountService
    get_user_subscriptions: GetUserSubscriptionsHandler
    get_subscription_items_handler: GetSubscriptionItemsHandler
    delete_subscription_items_handler: DeleteSubscriptionItemsHandler
    get_user_profile_handler: GetUserProfileHandler
    create_topic_handler: CreateTopicHandler
    get_user_topics_handler: GetUserTopicsHandler
    get_topic_handler: GetTopicHandler
    assign_subscription_to_topic_handler: AssignSubscriptionToTopicHandler
    unassign_subscription_from_topic_handler: UnassignSubscriptionFromUserTopicHandler
    get_topic_items_handler: GetTopicItemsHandler
    delete_topic_handler: DeleteUserTopicHandler
    update_topic_handler: UpdateTopicHandler
    get_item_handler: GetItemHandler
    create_item_interaction_handler: CreateItemInteractionHandler
    delete_item_interaction_handler: DeleteItemInteractionHandler
    add_external_credentials_handler: AddExternalCredentialsHandler
    get_user_external_credentials_handler: GetUserExternalCredentialsHandler
    delete_external_credential_handler: DeleteExternalCredentialHandler


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
            get_subscription_items_handler=handlers.get_subscription_items_handler,
            delete_subscription_items_handler=handlers.delete_subscription_items_handler),
        prefix="/subscriptions")
    app.include_router(
        items.get_router(
            get_session=get_current_session,
            get_item_handler=handlers.get_item_handler,
            create_item_interaction_handler=handlers.create_item_interaction_handler,
            delete_item_interaction_handler=handlers.delete_item_interaction_handler),
        prefix="/items")
    app.include_router(
        credentials.get_router(
            get_session=get_current_session,
            get_user_external_credentials_handler=handlers.get_user_external_credentials_handler,
            add_external_credential_handler=handlers.add_external_credentials_handler,
            delete_external_credential_handler=handlers.delete_external_credential_handler),
        prefix="/credentials"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    return app
