import asyncio
import logging

from linkurator_core.application.auth.send_validate_new_user_email import SendValidateNewUserEmail
from linkurator_core.application.auth.send_welcome_email import SendWelcomeEmail
from linkurator_core.application.common.event_handler import EventHandler
from linkurator_core.application.items.find_deprecated_items_handler import FindDeprecatedItemsHandler
from linkurator_core.application.items.find_zero_duration_items import FindZeroDurationItems
from linkurator_core.application.items.refresh_items_handler import RefreshItemsHandler
from linkurator_core.application.subscriptions.find_outdated_subscriptions_handler import \
    FindOutdatedSubscriptionsHandler
from linkurator_core.application.subscriptions.update_subscription_items_handler import UpdateSubscriptionItemsHandler
from linkurator_core.application.users.find_outdated_users_handler import FindOutdatedUsersHandler
from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.common.event import UserSubscriptionsBecameOutdatedEvent, SubscriptionBecameOutdatedEvent, \
    ItemsBecameOutdatedEvent, UserRegisterRequestSentEvent, UserRegisteredEvent
from linkurator_core.infrastructure.asyncio_impl.scheduler import TaskScheduler
from linkurator_core.infrastructure.asyncio_impl.utils import run_parallel, run_sequence, wait_until
from linkurator_core.infrastructure.config.env_settings import EnvSettings
from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.config.rabbitmq import RabbitMQSettings
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.gmail_email_sender import GmailEmailSender
from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient
from linkurator_core.infrastructure.google.youtube_rss_client import YoutubeRssClient
from linkurator_core.infrastructure.google.youtube_service import YoutubeService
from linkurator_core.infrastructure.mongodb.external_credentials_repository import MongodDBExternalCredentialRepository
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.registration_request_repository import MongoDBRegistrationRequestRepository
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository
from linkurator_core.infrastructure.rabbitmq_event_bus import RabbitMQEventBus

logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


async def main() -> None:  # pylint: disable=too-many-locals
    # Read settings
    env_settings = EnvSettings()
    db_settings = MongoDBSettings()
    google_secrets = GoogleClientSecrets(env_settings.GOOGLE_SECRET_PATH)
    rabbitmq_settings = RabbitMQSettings()

    # Repositories
    user_repository = MongoDBUserRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password
    )
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
        username=db_settings.user, password=db_settings.password
    )
    registration_request_repository = MongoDBRegistrationRequestRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password
    )

    # Services
    youtube_client = YoutubeApiClient()
    youtube_rss_client = YoutubeRssClient()
    account_service = GoogleAccountService(
        client_id=google_secrets.client_id,
        client_secret=google_secrets.client_secret)
    youtube_service = YoutubeService(
        google_account_service=account_service,
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        item_repository=item_repository,
        credentials_repository=credentials_repository,
        api_keys=google_secrets.api_keys,
        youtube_client=youtube_client,
        youtube_rss_client=youtube_rss_client
    )
    gmail_email_sender = GmailEmailSender(
        refresh_token=google_secrets.gmail_refresh_token,
        account_service=account_service)

    # Event bus
    event_bus = RabbitMQEventBus(host=str(rabbitmq_settings.address), port=rabbitmq_settings.port,
                                 username=rabbitmq_settings.user, password=rabbitmq_settings.password)

    # Event handlers
    update_user_subscriptions = UpdateUserSubscriptionsHandler(
        youtube_service, user_repository, subscription_repository)
    update_subscriptions_items = UpdateSubscriptionItemsHandler(
        subscription_repository=subscription_repository,
        item_repository=item_repository,
        subscription_service=youtube_service)
    refresh_items_handler = RefreshItemsHandler(
        item_repository=item_repository,
        subscription_service=youtube_service)
    find_outdated_users = FindOutdatedUsersHandler(user_repository, event_bus)
    find_outdated_subscriptions = FindOutdatedSubscriptionsHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus,
        user_repository=user_repository,
        external_credentials_repository=credentials_repository)
    find_deprecated_items = FindDeprecatedItemsHandler(
        item_repository=item_repository,
        event_bus=event_bus)
    find_zero_duration_items = FindZeroDurationItems(
        item_repository=item_repository,
        event_bus=event_bus)
    send_validate_new_user_email = SendValidateNewUserEmail(
        email_sender=gmail_email_sender,
        registration_request_repository=registration_request_repository,
        base_url=env_settings.VALIDATE_EMAIL_URL
    )
    send_welcome_email = SendWelcomeEmail(
        user_repository=user_repository,
        email_sender=gmail_email_sender,
        base_url=env_settings.WEBSITE_URL
    )

    event_handler = EventHandler(
        update_user_subscriptions_handler=update_user_subscriptions,
        update_subscription_items_handler=update_subscriptions_items,
        refresh_items_handler=refresh_items_handler,
        send_validate_new_user_email=send_validate_new_user_email,
        send_welcome_email=send_welcome_email
    )

    event_bus.subscribe(UserSubscriptionsBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(SubscriptionBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(ItemsBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(UserRegisterRequestSentEvent, event_handler.handle)
    event_bus.subscribe(UserRegisteredEvent, event_handler.handle)

    # Task scheduler
    scheduler = TaskScheduler()
    scheduler.schedule_recurring_task(task=find_outdated_users.handle, interval_seconds=60 * 5)
    scheduler.schedule_recurring_task(task=find_outdated_subscriptions.handle, interval_seconds=60)
    scheduler.schedule_recurring_task(task=find_deprecated_items.handle, interval_seconds=60 * 5)
    scheduler.schedule_recurring_task(task=find_zero_duration_items.handle, interval_seconds=60 * 5)

    await run_parallel(
        event_bus.start(),
        run_sequence(
            wait_until(event_bus.is_running),
            scheduler.start()
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
