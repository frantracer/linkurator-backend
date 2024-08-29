"""
Main file of the application
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from fastapi.applications import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.items.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.application.items.get_item_handler import GetItemHandler
from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.subscriptions.follow_subscription_handler import FollowSubscriptionHandler
from linkurator_core.application.subscriptions.get_subscription_handler import GetSubscriptionHandler
from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler
from linkurator_core.application.subscriptions.unfollow_subscription_handler import UnfollowSubscriptionHandler
from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import \
    AssignSubscriptionToTopicHandler
from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.topics.follow_topic_handler import FollowTopicHandler
from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsAsUserHandler
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.topics.unassign_subscription_from_user_topic_handler import \
    UnassignSubscriptionFromUserTopicHandler
from linkurator_core.application.topics.unfollow_topic_handler import UnfollowTopicHandler
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.application.users.add_external_credentials import AddExternalCredentialsHandler
from linkurator_core.application.users.delete_external_credential import DeleteExternalCredentialHandler
from linkurator_core.application.users.delete_user_handler import DeleteUserHandler
from linkurator_core.application.users.find_user_handler import FindCuratorHandler
from linkurator_core.application.users.follow_curator_handler import FollowCuratorHandler
from linkurator_core.application.users.get_curators_handler import GetCuratorsHandler
from linkurator_core.application.users.get_user_external_credentials import GetUserExternalCredentialsHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.users.register_user_handler import RegisterUserHandler
from linkurator_core.application.users.unfollow_curator_handler import UnfollowCuratorHandler
from linkurator_core.application.users.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.routers import authentication, profile, subscriptions, topics, items, \
    credentials, curators
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


@dataclass
class Handlers:  # pylint: disable=too-many-instance-attributes
    validate_token: ValidateTokenHandler
    register_user: RegisterUserHandler
    google_client: GoogleAccountService
    get_subscription: GetSubscriptionHandler
    get_user_subscriptions: GetUserSubscriptionsHandler
    follow_subscription_handler: FollowSubscriptionHandler
    unfollow_subscription_handler: UnfollowSubscriptionHandler
    get_subscription_items_handler: GetSubscriptionItemsHandler
    delete_subscription_items_handler: DeleteSubscriptionItemsHandler
    refresh_subscription_handler: RefreshSubscriptionHandler
    get_user_profile_handler: GetUserProfileHandler
    find_user_handler: FindCuratorHandler
    delete_user_handler: DeleteUserHandler
    get_curators_handler: GetCuratorsHandler
    follow_curator_handler: FollowCuratorHandler
    unfollow_curator_handler: UnfollowCuratorHandler
    create_topic_handler: CreateTopicHandler
    get_user_topics_handler: GetUserTopicsHandler
    get_curator_topics_as_user_handler: GetCuratorTopicsAsUserHandler
    get_curator_items_handler: GetCuratorItemsHandler
    get_topic_handler: GetTopicHandler
    assign_subscription_to_topic_handler: AssignSubscriptionToTopicHandler
    unassign_subscription_from_topic_handler: UnassignSubscriptionFromUserTopicHandler
    get_topic_items_handler: GetTopicItemsHandler
    delete_topic_handler: DeleteUserTopicHandler
    update_topic_handler: UpdateTopicHandler
    follow_topic_handler: FollowTopicHandler
    unfollow_topic_handler: UnfollowTopicHandler
    get_item_handler: GetItemHandler
    create_item_interaction_handler: CreateItemInteractionHandler
    delete_item_interaction_handler: DeleteItemInteractionHandler
    add_external_credentials_handler: AddExternalCredentialsHandler
    get_user_external_credentials_handler: GetUserExternalCredentialsHandler
    delete_external_credential_handler: DeleteExternalCredentialHandler


def create_app_from_handlers(handlers: Handlers) -> FastAPI:
    app = FastAPI(title="Linkurator API", version="0.1.0")

    async def get_current_session(request: Request) -> Optional[Session]:
        token = request.cookies.get("token")
        if token is None:
            return None
        session = await handlers.validate_token.handle(access_token=token)
        return session

    @app.get("/health", tags=["API Status"])
    async def health() -> str:
        """
        Health endpoint returns a 200 if the service is alive
        """
        return "OK"

    app.include_router(
        tags=["Authentication"],
        router=authentication.get_router(
            validate_token_handler=handlers.validate_token,
            register_user_handler=handlers.register_user,
            google_client=handlers.google_client))
    app.include_router(
        tags=["Profile"],
        router=profile.get_router(
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler,
            delete_user_handler=handlers.delete_user_handler
        ),
        prefix="/profile"
    )
    app.include_router(
        tags=["Curators"],
        router=curators.get_router(
            get_session=get_current_session,
            get_curators_handler=handlers.get_curators_handler,
            follow_curator_handler=handlers.follow_curator_handler,
            unfollow_curator_handler=handlers.unfollow_curator_handler,
            find_user_handler=handlers.find_user_handler,
            get_curator_topics_as_user=handlers.get_curator_topics_as_user_handler,
            get_curator_subscriptions_handler=handlers.get_user_subscriptions,
            get_curator_items_handler=handlers.get_curator_items_handler
        ),
        prefix="/curators"
    )
    app.include_router(
        tags=["Topics"],
        router=topics.get_router(
            get_session=get_current_session,
            create_topic_handler=handlers.create_topic_handler,
            get_topic_items_handler=handlers.get_topic_items_handler,
            get_topic_handler=handlers.get_topic_handler,
            get_user_topics_handler=handlers.get_user_topics_handler,
            assign_subscription_to_user_topic_handler=handlers.assign_subscription_to_topic_handler,
            unassign_subscription_from_user_topic_handler=handlers.unassign_subscription_from_topic_handler,
            delete_user_topic_handler=handlers.delete_topic_handler,
            update_user_topic_handler=handlers.update_topic_handler,
            follow_topic_handler=handlers.follow_topic_handler,
            unfollow_topic_handler=handlers.unfollow_topic_handler
        ),
        prefix="/topics")
    app.include_router(
        tags=["Subscriptions"],
        router=subscriptions.get_router(
            get_session=get_current_session,
            get_subscription_handler=handlers.get_subscription,
            get_user_subscriptions_handler=handlers.get_user_subscriptions,
            follow_subscription_handler=handlers.follow_subscription_handler,
            unfollow_subscription_handler=handlers.unfollow_subscription_handler,
            get_subscription_items_handler=handlers.get_subscription_items_handler,
            delete_subscription_items_handler=handlers.delete_subscription_items_handler,
            refresh_subscription_handler=handlers.refresh_subscription_handler),
        prefix="/subscriptions")
    app.include_router(
        tags=["Items"],
        router=items.get_router(
            get_session=get_current_session,
            get_item_handler=handlers.get_item_handler,
            create_item_interaction_handler=handlers.create_item_interaction_handler,
            delete_item_interaction_handler=handlers.delete_item_interaction_handler),
        prefix="/items")
    app.include_router(
        tags=["Credentials"],
        router=credentials.get_router(
            get_session=get_current_session,
            get_user_external_credentials_handler=handlers.get_user_external_credentials_handler,
            add_external_credential_handler=handlers.add_external_credentials_handler,
            delete_external_credential_handler=handlers.delete_external_credential_handler),
        prefix="/credentials"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://linkurator.com", "https://www.linkurator.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    return app
