from uuid import UUID

from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, TopicNotFoundError, UserNotFoundError
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


class AssignSubscriptionToTopicHandler:
    def __init__(self, user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository,
                 topic_repository: TopicRepository):
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.topic_repository = topic_repository

    def handle(self, user_id: UUID, subscription_id: UUID, topic_id: UUID) -> None:
        user = self.user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        subscription = self.subscription_repository.get(subscription_id)
        if subscription is None or subscription_id not in user.subscription_uuids:
            raise SubscriptionNotFoundError(subscription_id)

        topic = self.topic_repository.get(topic_id)
        if topic is None or topic.user_id != user_id:
            raise TopicNotFoundError(subscription_id)

        topic.add_subscription(subscription_id)

        self.topic_repository.update(topic)
