import asyncio
import logging

from linkurator_core.application.auth.send_validate_new_user_email import SendValidateNewUserEmail
from linkurator_core.application.auth.send_welcome_email import SendWelcomeEmail
from linkurator_core.application.common.event_handler import EventHandler
from linkurator_core.application.items.find_deprecated_items_handler import FindDeprecatedItemsHandler
from linkurator_core.application.items.find_zero_duration_items import FindZeroDurationItems
from linkurator_core.application.items.refresh_items_handler import RefreshItemsHandler
from linkurator_core.application.subscriptions.find_outdated_subscriptions_handler import (
    FindOutdatedSubscriptionsHandler,
)
from linkurator_core.application.subscriptions.find_subscriptions_with_outdated_items_handler import (
    FindSubscriptionsWithOutdatedItemsHandler,
)
from linkurator_core.application.subscriptions.update_subscription_handler import UpdateSubscriptionHandler
from linkurator_core.application.subscriptions.update_subscription_items_handler import UpdateSubscriptionItemsHandler
from linkurator_core.application.users.update_user_subscriptions_handler import UpdateUserSubscriptionsHandler
from linkurator_core.domain.common.event import (
    ItemsBecameOutdatedEvent,
    SubscriptionBecameOutdatedEvent,
    SubscriptionItemsBecameOutdatedEvent,
    UserRegisteredEvent,
    UserRegisterRequestSentEvent,
)
from linkurator_core.infrastructure.asyncio_impl.scheduler import TaskScheduler
from linkurator_core.infrastructure.asyncio_impl.utils import run_parallel, run_sequence, wait_until
from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.general_subscription_service import GeneralSubscriptionService
from linkurator_core.infrastructure.google.account_service import GoogleDomainAccountService
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
from linkurator_core.infrastructure.spotify.spotify_api_client import SpotifyApiClient
from linkurator_core.infrastructure.spotify.spotify_service import SpotifySubscriptionService

logging.basicConfig(format="%(asctime)s - %(levelname)s: %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")


async def main() -> None:  # pylint: disable=too-many-locals
    # Read settings
    settings = ApplicationSettings.from_file()
    db_settings = settings.mongodb
    google_secrets = settings.google
    spotify_secrets = settings.spotify
    rabbitmq_settings = settings.rabbitmq
    env_settings = settings.env

    # Repositories
    user_repository = MongoDBUserRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )
    subscription_repository = MongoDBSubscriptionRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )
    item_repository = MongoDBItemRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )
    credentials_repository = MongodDBExternalCredentialRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )
    registration_request_repository = MongoDBRegistrationRequestRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password,
    )

    # Services
    youtube_client = YoutubeApiClient()
    youtube_rss_client = YoutubeRssClient()
    youtube_service = YoutubeService(
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        item_repository=item_repository,
        credentials_repository=credentials_repository,
        api_keys=google_secrets.api_keys,
        youtube_client=youtube_client,
        youtube_rss_client=youtube_rss_client,
    )
    spotify_client = SpotifyApiClient(
        client_id=spotify_secrets.client_id,
        client_secret=spotify_secrets.client_secret,
    )
    spotify_service = SpotifySubscriptionService(
        spotify_client=spotify_client,
        user_repository=user_repository,
        item_repository=item_repository,
        subscription_repository=subscription_repository,
    )

    general_subscription_service = GeneralSubscriptionService(
        spotify_service=spotify_service,
        youtube_service=youtube_service,
    )

    google_domain_service = GoogleDomainAccountService(
        service_credentials_path=google_secrets.email_service_credentials_path,
        email=env_settings.GOOGLE_SERVICE_ACCOUNT_EMAIL,
    )
    gmail_email_sender = GmailEmailSender(account_service=google_domain_service)

    # Event bus
    event_bus = RabbitMQEventBus(host=str(rabbitmq_settings.address), port=rabbitmq_settings.port,
                                 username=rabbitmq_settings.user, password=rabbitmq_settings.password)

    # Event handlers
    update_user_subscriptions = UpdateUserSubscriptionsHandler(
        general_subscription_service, user_repository, subscription_repository)
    update_subscriptions_items = UpdateSubscriptionItemsHandler(
        subscription_repository=subscription_repository,
        item_repository=item_repository,
        subscription_service=general_subscription_service)
    update_subscription = UpdateSubscriptionHandler(
        subscription_repository=subscription_repository,
        subscription_service=general_subscription_service,
    )
    refresh_items_handler = RefreshItemsHandler(
        item_repository=item_repository,
        subscription_service=general_subscription_service)
    find_subscriptions_with_outdated_items = FindSubscriptionsWithOutdatedItemsHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus,
        user_repository=user_repository,
        external_credentials_repository=credentials_repository)
    find_outdated_subscriptions = FindOutdatedSubscriptionsHandler(
        subscription_repository=subscription_repository,
        event_bus=event_bus)
    find_deprecated_items = FindDeprecatedItemsHandler(
        item_repository=item_repository,
        event_bus=event_bus)
    find_zero_duration_items = FindZeroDurationItems(
        item_repository=item_repository,
        event_bus=event_bus)
    send_validate_new_user_email = SendValidateNewUserEmail(
        email_sender=gmail_email_sender,
        registration_request_repository=registration_request_repository,
    )
    send_welcome_email = SendWelcomeEmail(
        user_repository=user_repository,
        email_sender=gmail_email_sender,
        base_url=env_settings.WEBSITE_URL,
    )

    event_handler = EventHandler(
        update_user_subscriptions_handler=update_user_subscriptions,
        update_subscription_items_handler=update_subscriptions_items,
        update_subscription_handler=update_subscription,
        refresh_items_handler=refresh_items_handler,
        send_validate_new_user_email=send_validate_new_user_email,
        send_welcome_email=send_welcome_email,
    )

    event_bus.subscribe(SubscriptionItemsBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(SubscriptionBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(ItemsBecameOutdatedEvent, event_handler.handle)
    event_bus.subscribe(UserRegisterRequestSentEvent, event_handler.handle)
    event_bus.subscribe(UserRegisteredEvent, event_handler.handle)

    # Task scheduler
    scheduler = TaskScheduler()
    scheduler.schedule_recurring_task(task=find_subscriptions_with_outdated_items.handle, interval_seconds=60)
    scheduler.schedule_recurring_task(task=find_outdated_subscriptions.handle, interval_seconds=60 * 5)
    scheduler.schedule_recurring_task(task=find_deprecated_items.handle, interval_seconds=60 * 5)
    scheduler.schedule_recurring_task(task=find_zero_duration_items.handle, interval_seconds=60 * 5)

    await run_parallel(
        event_bus.start(),
        run_sequence(
            wait_until(event_bus.is_running),
            scheduler.start(),
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
