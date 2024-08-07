from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


class CreateTopicHandler:
    def __init__(self, topic_repository: TopicRepository) -> None:
        self.topic_repository = topic_repository

    async def handle(self, topic: Topic) -> None:
        try:
            await self.topic_repository.add(topic)
        except DuplicatedKeyError as err:
            print(f'Duplicated key error: {err}')
