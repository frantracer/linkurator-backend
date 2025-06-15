"""Main file of the application."""
import logging

from fastapi.applications import FastAPI

from linkurator_core.application.auth.change_password_from_request import ChangePasswordFromRequest
from linkurator_core.application.auth.register_new_user_with_email import RegisterNewUserWithEmail
from linkurator_core.application.auth.register_new_user_with_google import RegisterUserHandler
from linkurator_core.application.auth.request_password_change import RequestPasswordChange
from linkurator_core.application.auth.validate_new_user_request import ValidateNewUserRequest
from linkurator_core.application.auth.validate_session_token import ValidateTokenHandler
from linkurator_core.application.auth.validate_user_password import ValidateUserPassword
from linkurator_core.application.items.create_item_interaction_handler import CreateItemInteractionHandler
from linkurator_core.application.items.delete_item_interaction_handler import DeleteItemInteractionHandler
from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.application.items.get_curator_items_handler import GetCuratorItemsHandler
from linkurator_core.application.items.get_item_handler import GetItemHandler
from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.statistics.get_platform_statistics import GetPlatformStatisticsHandler
from linkurator_core.application.subscriptions.find_subscription_by_name_or_url_handler import (
    FindSubscriptionsByNameOrUrlHandler,
)
from linkurator_core.application.subscriptions.follow_subscription_handler import FollowSubscriptionHandler
from linkurator_core.application.subscriptions.get_subscription_handler import GetSubscriptionHandler
from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.subscriptions.refresh_subscription_handler import RefreshSubscriptionHandler
from linkurator_core.application.subscriptions.unfollow_subscription_handler import UnfollowSubscriptionHandler
from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import (
    AssignSubscriptionToTopicHandler,
)
from linkurator_core.application.topics.create_topic_handler import CreateTopicHandler
from linkurator_core.application.topics.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.topics.find_topics_by_name_handler import FindTopicsByNameHandler
from linkurator_core.application.topics.follow_topic_handler import FollowTopicHandler
from linkurator_core.application.topics.get_curator_topics_as_user_handler import GetCuratorTopicsHandler
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.topics.unassign_subscription_from_user_topic_handler import (
    UnassignSubscriptionFromUserTopicHandler,
)
from linkurator_core.application.topics.unfollow_topic_handler import UnfollowTopicHandler
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.application.users.add_external_credentials import AddExternalCredentialsHandler
from linkurator_core.application.users.delete_external_credential import DeleteExternalCredentialHandler
from linkurator_core.application.users.delete_user_handler import DeleteUserHandler
from linkurator_core.application.users.edit_user_profile import EditUserProfile
from linkurator_core.application.users.find_user_handler import FindCuratorHandler
from linkurator_core.application.users.follow_curator_handler import FollowCuratorHandler
from linkurator_core.application.users.get_curators_handler import GetCuratorsHandler
from linkurator_core.application.users.get_user_external_credentials import GetUserExternalCredentialsHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.users.unfollow_curator_handler import UnfollowCuratorHandler
from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.infrastructure.config.env_settings import EnvSettings
from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets, SpotifyClientSecrets
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.config.rabbitmq import RabbitMQSettings
from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app_from_handlers
from linkurator_core.infrastructure.general_subscription_service import GeneralSubscriptionService
from linkurator_core.infrastructure.google.account_service import GoogleAccountService, GoogleDomainAccountService
from linkurator_core.infrastructure.google.gmail_email_sender import GmailEmailSender
from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient
from linkurator_core.infrastructure.google.youtube_api_key_checker import YoutubeApiKeyChecker
from linkurator_core.infrastructure.google.youtube_rss_client import YoutubeRssClient
from linkurator_core.infrastructure.google.youtube_service import YoutubeService
from linkurator_core.infrastructure.mongodb.external_credentials_repository import MongodDBExternalCredentialRepository
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.password_change_request_repository import (
    MongoDBPasswordChangeRequestRepository,
)
from linkurator_core.infrastructure.mongodb.registration_request_repository import MongoDBRegistrationRequestRepository
from linkurator_core.infrastructure.mongodb.session_repository import MongoDBSessionRepository
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository
from linkurator_core.infrastructure.mongodb.topic_repository import MongoDBTopicRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository
from linkurator_core.infrastructure.rabbitmq_event_bus import RabbitMQEventBus
from linkurator_core.infrastructure.spotify.spotify_api_client import SpotifyApiClient
from linkurator_core.infrastructure.spotify.spotify_service import SpotifySubscriptionService


def app_handlers() -> Handlers:
    env_settings = EnvSettings()

    spotify_secrets = SpotifyClientSecrets(env_settings.SPOTIFY_SECRET_PATH)
    google_secrets = GoogleClientSecrets(env_settings.GOOGLE_SECRET_PATH)
    account_service = GoogleAccountService(
        client_id=google_secrets.client_id,
        client_secret=google_secrets.client_secret)
    google_secrets_youtube = GoogleClientSecrets(env_settings.GOOGLE_YOUTUBE_SECRET_PATH)
    youtube_account_service = GoogleAccountService(
        client_id=google_secrets_youtube.client_id,
        client_secret=google_secrets_youtube.client_secret,
    )

    logging.getLogger("pymongo").setLevel(logging.INFO)

    db_settings = MongoDBSettings()
    user_repository = MongoDBUserRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    session_repository = MongoDBSessionRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    subscription_repository = MongoDBSubscriptionRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    item_repository = MongoDBItemRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    topic_repository = MongoDBTopicRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    credentials_repository = MongodDBExternalCredentialRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    registration_request_repository = MongoDBRegistrationRequestRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    password_change_request_repository = MongoDBPasswordChangeRequestRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)
    credentials_checker = YoutubeApiKeyChecker()

    youtube_service = YoutubeService(
        subscription_repository=subscription_repository,
        user_repository=user_repository,
        item_repository=item_repository,
        credentials_repository=credentials_repository,
        youtube_client=YoutubeApiClient(),
        youtube_rss_client=YoutubeRssClient(),
        api_keys=google_secrets.api_keys,
    )

    spotify_client = SpotifyApiClient(
        client_id=spotify_secrets.client_id,
        client_secret=spotify_secrets.client_secret,
    )

    spotify_service = SpotifySubscriptionService(
        spotify_client=spotify_client,
        subscription_repository=subscription_repository,
        user_repository=user_repository,
        item_repository=item_repository,
    )

    general_subscription_service = GeneralSubscriptionService(
        spotify_service=spotify_service,
        youtube_service=youtube_service,
    )

    rabbitmq_settings = RabbitMQSettings()
    event_bus = RabbitMQEventBus(host=str(rabbitmq_settings.address), port=rabbitmq_settings.port,
                                 username=rabbitmq_settings.user, password=rabbitmq_settings.password)

    google_domain_service = GoogleDomainAccountService(
        service_credentials_path=google_secrets.email_service_credentials_path,
        email=env_settings.GOOGLE_SERVICE_ACCOUNT_EMAIL,
    )
    email_sender = GmailEmailSender(account_service=google_domain_service)

    RegistrationRequest.valid_domains = env_settings.VALID_DOMAINS
    PasswordChangeRequest.valid_domains = env_settings.VALID_DOMAINS

    return Handlers(
        validate_token=ValidateTokenHandler(user_repository, session_repository, account_service),
        validate_user_password=ValidateUserPassword(user_repository, session_repository),
        register_user_with_google=RegisterUserHandler(user_repository, account_service, event_bus),
        register_user_with_email=RegisterNewUserWithEmail(
            user_repository=user_repository,
            registration_request_repository=registration_request_repository,
            event_bus=event_bus),
        validate_new_user_request=ValidateNewUserRequest(
            user_repository=user_repository,
            registration_request_repository=registration_request_repository,
            event_bus=event_bus),
        request_password_change=RequestPasswordChange(
            user_repository=user_repository,
            password_change_request_repository=password_change_request_repository,
            email_sender=email_sender),
        change_password_from_request=ChangePasswordFromRequest(
            user_repository=user_repository,
            request_repository=password_change_request_repository),
        google_client=account_service,
        google_youtube_client=youtube_account_service,
        get_user_subscriptions=GetUserSubscriptionsHandler(subscription_repository, user_repository),
        follow_subscription_handler=FollowSubscriptionHandler(subscription_repository, user_repository),
        unfollow_subscription_handler=UnfollowSubscriptionHandler(
            subscription_repository, user_repository, topic_repository),
        get_subscription=GetSubscriptionHandler(subscription_repository),
        get_subscription_items_handler=GetSubscriptionItemsHandler(
            item_repository=item_repository,
            subscription_repository=subscription_repository,
        ),
        delete_subscription_items_handler=DeleteSubscriptionItemsHandler(
            item_repository=item_repository,
            subscription_repository=subscription_repository,
            user_repository=user_repository),
        refresh_subscription_handler=RefreshSubscriptionHandler(
            subscription_repository=subscription_repository,
            subscription_service=general_subscription_service,
            event_bus=event_bus,
        ),
        get_user_profile_handler=GetUserProfileHandler(user_repository),
        edit_user_profile_handler=EditUserProfile(user_repository),
        find_user_handler=FindCuratorHandler(user_repository),
        delete_user_handler=DeleteUserHandler(user_repository, session_repository, account_service),
        get_curators_handler=GetCuratorsHandler(user_repository),
        find_subscriptions_by_name_handler=FindSubscriptionsByNameOrUrlHandler(
            subscription_repository=subscription_repository,
            subscription_service=general_subscription_service,
            event_bus=event_bus,
        ),
        follow_curator_handler=FollowCuratorHandler(user_repository),
        unfollow_curator_handler=UnfollowCuratorHandler(user_repository),
        get_user_topics_handler=GetUserTopicsHandler(
            topic_repo=topic_repository,
            user_repo=user_repository,
        ),
        get_curator_topics_handler=GetCuratorTopicsHandler(
            user_repository=user_repository,
            topic_repository=topic_repository),
        find_topics_by_name_handler=FindTopicsByNameHandler(
            topic_repository=topic_repository,
            user_repository=user_repository,
        ),
        get_curator_items_handler=GetCuratorItemsHandler(
            item_repository=item_repository,
            subscription_repository=subscription_repository,
        ),
        create_topic_handler=CreateTopicHandler(topic_repository=topic_repository),
        get_topic_items_handler=GetTopicItemsHandler(
            topic_repository=topic_repository,
            subscription_repository=subscription_repository,
            item_repository=item_repository),
        assign_subscription_to_topic_handler=AssignSubscriptionToTopicHandler(
            subscription_repository=subscription_repository,
            topic_repository=topic_repository,
            user_repository=user_repository),
        update_topic_handler=UpdateTopicHandler(
            topic_repository=topic_repository,
            subscription_repository=subscription_repository),
        delete_topic_handler=DeleteUserTopicHandler(topic_repository=topic_repository),
        get_topic_handler=GetTopicHandler(
            topic_repository=topic_repository,
            user_repository=user_repository,
        ),
        unassign_subscription_from_topic_handler=UnassignSubscriptionFromUserTopicHandler(
            topic_repository=topic_repository),
        follow_topic_handler=FollowTopicHandler(
            user_repository=user_repository,
            topic_repository=topic_repository),
        unfollow_topic_handler=UnfollowTopicHandler(
            user_repository=user_repository ),
        get_item_handler=GetItemHandler(
            item_repository=item_repository,
            subscription_repository=subscription_repository,
        ),
        create_item_interaction_handler=CreateItemInteractionHandler(
            item_repository=item_repository),
        delete_item_interaction_handler=DeleteItemInteractionHandler(
            item_repository=item_repository),
        add_external_credentials_handler=AddExternalCredentialsHandler(
            credentials_repository=credentials_repository,
            credential_checker=credentials_checker),
        get_user_external_credentials_handler=GetUserExternalCredentialsHandler(
            credentials_repository=credentials_repository),
        delete_external_credential_handler=DeleteExternalCredentialHandler(
            credentials_repository=credentials_repository),
        get_platform_statistics=GetPlatformStatisticsHandler(
            user_repository=user_repository,
            subscription_repository=subscription_repository),
        update_user_subscriptions_handler=UpdateUserSubscriptionsHandler(
            subscription_service=youtube_service,
            user_repository=user_repository,
            subscription_repository=subscription_repository),
    )


def create_app() -> FastAPI:
    logging.basicConfig(format="%(asctime)s - %(levelname)s: %(message)s",
                        level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")
    return create_app_from_handlers(app_handlers())
