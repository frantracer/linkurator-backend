import asyncio
import logging
import os

from linkurator_core.application.common.event_handler import EventHandler
from linkurator_core.application.subscriptions.find_outdated_subscriptions_handler import \
    FindOutdatedSubscriptionsHandler
from linkurator_core.application.subscriptions.update_subscription_items_handler import UpdateSubscriptionItemsHandler
from linkurator_core.application.users.find_outdated_users_handler import FindOutdatedUsersHandler
from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent, SubscriptionBecameOutdatedEvent
from linkurator_core.infrastructure.asyncio.event_bus_service import AsyncioEventBusService
from linkurator_core.infrastructure.asyncio.scheduler import TaskScheduler
from linkurator_core.infrastructure.asyncio.utils import run_parallel
from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeService, YoutubeApiClient
from linkurator_core.infrastructure.mongodb.external_credentials_repository import MongodDBExternalCredentialRepository
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository

logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


async def main():  # pylint: disable=too-many-locals
    # Repositories
    db_settings = MongoDBSettings()
    user_repository = MongoDBUserRepository(ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
                                            username=db_settings.user, password=db_settings.password)
    subscription_repository = MongoDBSubscriptionRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password
    )
    item_repository = MongoDBItemRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password
    )
    credentials_repository = MongodDBExternalCredentialRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)

    # Services
    google_client_secret_path = os.environ.get('LINKURATOR_GOOGLE_SECRET_PATH', "secrets/client_secret.json")
    google_secrets = GoogleClientSecrets(google_client_secret_path)
    youtube_client = YoutubeApiClient()
    account_service = GoogleAccountService(
        client_id=google_secrets.client_id,
        client_secret=google_secrets.client_secret)
    youtube_service = YoutubeService(
        google_account_service=account_service,
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        credentials_repository=credentials_repository,
        api_key=google_secrets.api_key,
        youtube_client=youtube_client)

    # Event bus
    event_bus = AsyncioEventBusService()

    # Event handlers
    update_user_subscriptions = UpdateUserSubscriptionsHandler(
        youtube_service, user_repository, subscription_repository)
    update_subscriptions_items = UpdateSubscriptionItemsHandler(
        subscription_repository=subscription_repository,
        item_repository=item_repository,
        subscription_service=youtube_service)
    find_outdated_users = FindOutdatedUsersHandler(user_repository, event_bus)
    find_outdated_subscriptions = FindOutdatedSubscriptionsHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus,
        user_repository=user_repository,
        external_credentials_repository=credentials_repository)
    event_handler = EventHandler(
        update_user_subscriptions_handler=update_user_subscriptions,
        update_subscription_items_handler=update_subscriptions_items)

    event_bus.subscribe(UserSubscriptionsBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(SubscriptionBecameOutdatedEvent, event_handler.handle)

    # Task scheduler
    scheduler = TaskScheduler()
    scheduler.schedule_recurring_task(task=find_outdated_users.handle, interval_seconds=60 * 5)
    scheduler.schedule_recurring_task(task=find_outdated_subscriptions.handle, interval_seconds=60)

    await run_parallel(
        event_bus.start(),
        scheduler.start()
    )


if __name__ == "__main__":
    asyncio.run(main())
