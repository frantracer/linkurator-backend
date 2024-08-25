from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError, CannotUnfollowAssignedSubscriptionError
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


class UnfollowSubscriptionHandler:
    def __init__(
            self,
            subscription_repository: SubscriptionRepository,
            user_repository: UserRepository,
            topic_repository: TopicRepository
    ) -> None:
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository
        self.topic_repository = topic_repository

    async def handle(self, user_id: UUID, subscription_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        topics = await self.topic_repository.get_by_user_id(user_id)
        if any(subscription_id in topic.subscriptions_ids for topic in topics):
            raise CannotUnfollowAssignedSubscriptionError(subscription_id)

        user.unfollow_subscription(subscription_id)

        await self.user_repository.update(user)
