from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


class CreateTopicHandler:
    def __init__(self, topic_repository: TopicRepository):
        self.topic_repository = topic_repository

    def handle(self, topic: Topic) -> None:
        try:
            self.topic_repository.add(topic)
        except DuplicatedKeyError as err:
            print(f'Duplicated key error: {err}')
