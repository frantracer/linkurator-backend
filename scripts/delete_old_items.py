import argparse
import logging
import sys
from datetime import datetime, timezone

from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.domain.items.item_repository import ItemFilterCriteria
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository
from linkurator_core.infrastructure.mongodb.user_repository import MongoDBUserRepository

logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--admin-email', type=str, required=True)
    args = parser.parse_args()

    db_settings = MongoDBSettings()
    item_repository = MongoDBItemRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)

    subscription_repository = MongoDBSubscriptionRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)

    user_repository = MongoDBUserRepository(
        ip=db_settings.address, port=db_settings.port, db_name=db_settings.db_name,
        username=db_settings.user, password=db_settings.password)

    delete_subscription_items = DeleteSubscriptionItemsHandler(
        user_repository=user_repository,
        subscription_repository=subscription_repository,
        item_repository=item_repository)

    is_there_and_outdated_subscription = True

    admin = user_repository.get_by_email(args.admin_email)
    if admin is None:
        logging.error('Admin user not found')
        sys.exit(1)

    while is_there_and_outdated_subscription:
        items, _ = item_repository.find_items(
            criteria=ItemFilterCriteria(created_before=datetime.now(tz=timezone.utc)),
            page_number=0, limit=1)

        subscriptions_uuids = set()
        for item in items:
            subscriptions_uuids.add(item.subscription_uuid)

        logging.info("Found %s subscriptions to delete", len(subscriptions_uuids))

        for subscription_uuid in subscriptions_uuids:
            logging.info("Deleting items for subscription with uuid: %s", subscription_uuid)
            delete_subscription_items.handle(admin.uuid, subscription_uuid)

        if len(subscriptions_uuids) == 0:
            is_there_and_outdated_subscription = False


if __name__ == '__main__':
    main()
