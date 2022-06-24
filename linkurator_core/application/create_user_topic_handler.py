from linkurator_core.domain.topic import Topic
from linkurator_core.domain.topic_repository import TopicRepository


class CreateTopicHandler:
    def __init__(self, topic_repository: TopicRepository):
        self.topic_repository = topic_repository

    def handle(self, topic: Topic) -> None:
        self.topic_repository.add(topic)
