from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


class FindTopicsByNameHandler:
    def __init__(self, topic_repository: TopicRepository):
        self.topic_repository = topic_repository

    async def handle(self, name: str) -> list[Topic]:
        return await self.topic_repository.find_topics_by_name(name)
