from typing import List
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


class GetUserTopicsHandler:
    def __init__(self, user_repo: UserRepository, topic_repo: TopicRepository) -> None:
        self.user_repo = user_repo
        self.topic_repo = topic_repo

    def handle(self, user_id: UUID) -> List[Topic]:
        user = self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        return self.topic_repo.get_by_user_id(user_id)
