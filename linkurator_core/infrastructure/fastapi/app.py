"""
Main file of the application
"""
import os

from fastapi.applications import FastAPI

from linkurator_core.application.assign_subscription_to_user_topic_handler import AssignSubscriptionToTopicHandler
from linkurator_core.application.create_user_topic_handler import CreateTopicHandler
from linkurator_core.application.delete_user_topic_handler import DeleteUserTopicHandler
from linkurator_core.application.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.get_topic_handler import GetTopicHandler
from linkurator_core.application.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.application.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.application.unassign_subscription_from_user_topic_handler import \
    UnassignSubscriptionFromUserTopicHandler
from linkurator_core.application.validate_token_handler import ValidateTokenHandler
from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.session_repository import MongoDBSessionRepository
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository
from linkurator_core.infrastructure.mongodb.topic_repository import MongoDBTopicRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository

google_client_secret_path = os.environ.get('LINKURATOR_GOOGLE_SECRET_PATH', "secrets/client_secret.json")
google_secrets = GoogleClientSecrets(google_client_secret_path)
account_service = GoogleAccountService(
    client_id=google_secrets.client_id,
    client_secret=google_secrets.client_secret)

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

app_handlers = Handlers(
    validate_token=ValidateTokenHandler(user_repository, session_repository, account_service),
    google_client=account_service,
    get_user_subscriptions=GetUserSubscriptionsHandler(subscription_repository, user_repository),
    get_subscription_items_handler=GetSubscriptionItemsHandler(item_repository),
    get_user_profile_handler=GetUserProfileHandler(user_repository),
    get_user_topics_handler=GetUserTopicsHandler(topic_repo=topic_repository, user_repo=user_repository),
    create_user_topic_handler=CreateTopicHandler(topic_repository=topic_repository),
    get_topic_items_handler=GetTopicItemsHandler(topic_repository=topic_repository, item_repository=item_repository),
    assign_subscription_to_topic_handler=AssignSubscriptionToTopicHandler(
        subscription_repository=subscription_repository,
        topic_repository=topic_repository,
        user_repository=user_repository),
    delete_topic_handler=DeleteUserTopicHandler(topic_repository=topic_repository),
    get_topic_handler=GetTopicHandler(topic_repository=topic_repository),
    unassign_subscription_from_topic_handler=UnassignSubscriptionFromUserTopicHandler(
        topic_repository=topic_repository)
)

# FastAPI application
app: FastAPI = create_app(app_handlers)
