"""Main file of the application."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.applications import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from linkurator_core.application.auth.change_password_from_request import ChangePasswordFromRequest
from linkurator_core.application.auth.register_new_user_with_email import RegisterNewUserWithEmail
from linkurator_core.application.auth.register_new_user_with_google import RegisterUserHandler
from linkurator_core.application.auth.request_password_change import RequestPasswordChange
from linkurator_core.application.auth.validate_new_user_request import ValidateNewUserRequest
from linkurator_core.application.auth.validate_session_token import ValidateTokenHandler
from linkurator_core.application.auth.validate_user_password import ValidateUserPassword
from linkurator_core.application.chats.delete_chat_handler import DeleteChatHandler
from linkurator_core.application.chats.get_chat_handler import GetChatHandler
from linkurator_core.application.chats.get_user_chats_handler import GetUserChatsHandler
from linkurator_core.application.chats.query_agent_handler import QueryAgentHandler
from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.items.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.application.items.get_followed_subscriptions_items_handler import (
    GetFollowedSubscriptionsItemsHandler,
)
from linkurator_core.application.items.get_item_handler import GetItemHandler
from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.statistics.get_platform_statistics import (
    GetPlatformStatisticsHandler,
    PlatformStatistics,
)
from linkurator_core.application.subscriptions.find_subscription_by_name_or_url_handler import (
    FindSubscriptionsByNameOrUrlHandler,
)
from linkurator_core.application.subscriptions.follow_subscription_handler import FollowSubscriptionHandler
from linkurator_core.application.subscriptions.get_providers_handler import GetProvidersHandler
from linkurator_core.application.subscriptions.get_subscription_handler import GetSubscriptionHandler
from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler
from linkurator_core.application.subscriptions.unfollow_subscription_handler import UnfollowSubscriptionHandler
from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import (
    AssignSubscriptionToTopicHandler,
)
from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.topics.favorite_topic_handler import FavoriteTopicHandler
from linkurator_core.application.topics.find_topics_by_name_handler import FindTopicsByNameHandler
from linkurator_core.application.topics.follow_topic_handler import FollowTopicHandler
from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsHandler
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.topics.unassign_subscription_from_user_topic_handler import (
    UnassignSubscriptionFromUserTopicHandler,
)
from linkurator_core.application.topics.unfavorite_topic_handler import UnfavoriteTopicHandler
from linkurator_core.application.topics.unfollow_topic_handler import UnfollowTopicHandler
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.application.users.delete_user_filter_handler import DeleteUserFilterHandler
from linkurator_core.application.users.delete_user_handler import DeleteUserHandler
from linkurator_core.application.users.edit_user_profile import EditUserProfile
from linkurator_core.application.users.find_user_handler import FindCuratorHandler
from linkurator_core.application.users.follow_curator_handler import FollowCuratorHandler
from linkurator_core.application.users.get_curators_handler import GetCuratorsHandler
from linkurator_core.application.users.get_user_filter_handler import GetUserFilterHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.users.unfollow_curator_handler import UnfollowCuratorHandler
from linkurator_core.application.users.update_user_subscriptions_handler import UpdateYoutubeUserSubscriptionsHandler
from linkurator_core.application.users.upsert_user_filter_handler import UpsertUserFilterHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.routers import (
    authentication,
    chats,
    curators,
    items,
    profile,
    providers,
    subscriptions,
    topics,
    user_filter,
)
from linkurator_core.infrastructure.fastapi.routers.authentication import check_basic_auth
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


@dataclass
class Handlers:  # pylint: disable=too-many-instance-attributes
    validate_token: ValidateTokenHandler
    validate_user_password: ValidateUserPassword
    register_user_with_google: RegisterUserHandler
    register_user_with_email: RegisterNewUserWithEmail
    validate_new_user_request: ValidateNewUserRequest
    request_password_change: RequestPasswordChange
    change_password_from_request: ChangePasswordFromRequest
    google_client: GoogleAccountService
    google_youtube_client: GoogleAccountService
    get_subscription: GetSubscriptionHandler
    get_user_subscriptions: GetUserSubscriptionsHandler
    find_subscriptions_by_name_handler: FindSubscriptionsByNameOrUrlHandler
    follow_subscription_handler: FollowSubscriptionHandler
    unfollow_subscription_handler: UnfollowSubscriptionHandler
    get_subscription_items_handler: GetSubscriptionItemsHandler
    delete_subscription_items_handler: DeleteSubscriptionItemsHandler
    refresh_subscription_handler: RefreshSubscriptionHandler
    get_user_profile_handler: GetUserProfileHandler
    edit_user_profile_handler: EditUserProfile
    find_user_handler: FindCuratorHandler
    delete_user_handler: DeleteUserHandler
    get_curators_handler: GetCuratorsHandler
    follow_curator_handler: FollowCuratorHandler
    unfollow_curator_handler: UnfollowCuratorHandler
    create_topic_handler: CreateTopicHandler
    get_user_topics_handler: GetUserTopicsHandler
    get_curator_topics_handler: GetCuratorTopicsHandler
    get_curator_items_handler: GetCuratorItemsHandler
    get_topic_handler: GetTopicHandler
    find_topics_by_name_handler: FindTopicsByNameHandler
    assign_subscription_to_topic_handler: AssignSubscriptionToTopicHandler
    unassign_subscription_from_topic_handler: UnassignSubscriptionFromUserTopicHandler
    get_topic_items_handler: GetTopicItemsHandler
    delete_topic_handler: DeleteUserTopicHandler
    update_topic_handler: UpdateTopicHandler
    follow_topic_handler: FollowTopicHandler
    unfollow_topic_handler: UnfollowTopicHandler
    favorite_topic_handler: FavoriteTopicHandler
    unfavorite_topic_handler: UnfavoriteTopicHandler
    get_item_handler: GetItemHandler
    create_item_interaction_handler: CreateItemInteractionHandler
    delete_item_interaction_handler: DeleteItemInteractionHandler
    get_followed_subscriptions_items_handler: GetFollowedSubscriptionsItemsHandler
    get_platform_statistics: GetPlatformStatisticsHandler
    get_providers_handler: GetProvidersHandler
    update_youtube_user_subscriptions_handler: UpdateYoutubeUserSubscriptionsHandler
    query_agent_handler: QueryAgentHandler
    get_user_chats_handler: GetUserChatsHandler
    get_chat_handler: GetChatHandler
    delete_chat_handler: DeleteChatHandler
    get_user_filter_handler: GetUserFilterHandler
    upsert_user_filter_handler: UpsertUserFilterHandler
    delete_user_filter_handler: DeleteUserFilterHandler


def create_app_from_handlers(handlers: Handlers) -> FastAPI:
    app = FastAPI(title="Linkurator API", version="0.1.0")

    async def get_current_session(request: Request) -> Session | None:
        token = request.cookies.get("token")
        if token is None:
            return None
        return await handlers.validate_token.handle(access_token=token)

    @app.get("/health", tags=["API Status"])
    async def health() -> str:
        """Health endpoint returns a 200 if the service is alive."""
        return "OK"

    @app.get("/statistics", tags=["API Status"])
    async def statistics(
            _: None = Depends(check_basic_auth),
    ) -> PlatformStatistics:
        """Returns platform statistics."""
        return await handlers.get_platform_statistics.handle()

    app.include_router(
        tags=["Authentication"],
        router=authentication.get_router(
            google_client=handlers.google_client,
            validate_token=handlers.validate_token,
            validate_user_password=handlers.validate_user_password,
            register_user_with_google=handlers.register_user_with_google,
            register_user_with_email=handlers.register_user_with_email,
            validate_new_user_request=handlers.validate_new_user_request,
            request_password_change=handlers.request_password_change,
            change_password_from_request=handlers.change_password_from_request,
        ),
    )
    app.include_router(
        tags=["Profile"],
        router=profile.get_router(
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler,
            edit_user_profile_handler=handlers.edit_user_profile_handler,
            delete_user_handler=handlers.delete_user_handler,
        ),
        prefix="/profile",
    )
    app.include_router(
        tags=["Curators"],
        router=curators.get_router(
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler,
            get_curators_handler=handlers.get_curators_handler,
            follow_curator_handler=handlers.follow_curator_handler,
            unfollow_curator_handler=handlers.unfollow_curator_handler,
            find_user_handler=handlers.find_user_handler,
            get_curator_topics_handler=handlers.get_curator_topics_handler,
            get_curator_subscriptions_handler=handlers.get_user_subscriptions,
            get_curator_items_handler=handlers.get_curator_items_handler,
        ),
        prefix="/curators",
    )
    app.include_router(
        tags=["Topics"],
        router=topics.get_router(
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler,
            create_topic_handler=handlers.create_topic_handler,
            get_topic_items_handler=handlers.get_topic_items_handler,
            get_topic_handler=handlers.get_topic_handler,
            get_user_topics_handler=handlers.get_user_topics_handler,
            find_topics_by_name_handler=handlers.find_topics_by_name_handler,
            assign_subscription_to_user_topic_handler=handlers.assign_subscription_to_topic_handler,
            unassign_subscription_from_user_topic_handler=handlers.unassign_subscription_from_topic_handler,
            delete_user_topic_handler=handlers.delete_topic_handler,
            update_user_topic_handler=handlers.update_topic_handler,
            follow_topic_handler=handlers.follow_topic_handler,
            unfollow_topic_handler=handlers.unfollow_topic_handler,
            favorite_topic_handler=handlers.favorite_topic_handler,
            unfavorite_topic_handler=handlers.unfavorite_topic_handler,
        ),
        prefix="/topics")
    app.include_router(
        tags=["Subscriptions"],
        router=subscriptions.get_router(
            google_client=handlers.google_youtube_client,
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler,
            get_subscription_handler=handlers.get_subscription,
            get_user_subscriptions_handler=handlers.get_user_subscriptions,
            find_subscriptions_by_name_or_url=handlers.find_subscriptions_by_name_handler,
            follow_subscription_handler=handlers.follow_subscription_handler,
            unfollow_subscription_handler=handlers.unfollow_subscription_handler,
            get_subscription_items_handler=handlers.get_subscription_items_handler,
            delete_subscription_items_handler=handlers.delete_subscription_items_handler,
            refresh_subscription_handler=handlers.refresh_subscription_handler,
            update_user_subscriptions_handler=handlers.update_youtube_user_subscriptions_handler,
            get_followed_subscriptions_items_handler=handlers.get_followed_subscriptions_items_handler,
        ),
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
        tags=["Providers"],
        router=providers.get_router(
            get_providers_handler=handlers.get_providers_handler,
        ),
        prefix="/providers",
    )
    app.include_router(
        tags=["Chats"],
        router=chats.get_router(
            get_session=get_current_session,
            query_agent_handler=handlers.query_agent_handler,
            get_user_chats_handler=handlers.get_user_chats_handler,
            get_chat_handler=handlers.get_chat_handler,
            delete_chat_handler=handlers.delete_chat_handler,
        ),
        prefix="/chats",
    )
    app.include_router(
        tags=["User Filter"],
        router=user_filter.get_router(
            get_session=get_current_session,
            get_user_filter_handler=handlers.get_user_filter_handler,
            upsert_user_filter_handler=handlers.upsert_user_filter_handler,
            delete_user_filter_handler=handlers.delete_user_filter_handler,
        ),
        prefix="/filters",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://linkurator.com", "https://www.linkurator.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
