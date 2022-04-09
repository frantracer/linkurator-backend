from datetime import datetime
from typing import List
from uuid import UUID

from pydantic.main import BaseModel


class NewTopicSchema(BaseModel):
    """
    Input model for topic creation
    """
    uuid: UUID
    name: str
    subscriptions_ids: List[UUID]

    def __init__(self, uuid: UUID, name: str, subscriptions_ids: List[UUID]):
        super().__init__(uuid=uuid, name=name, subscriptions_ids=subscriptions_ids)


class TopicSchema(BaseModel):
    """
    Category that includes different subscriptions
    """
    uuid: UUID
    name: str
    subscriptions_ids: List[UUID]
    created_at: datetime

    def __init__(self, uuid: UUID, name: str, subscriptions_ids: List[UUID],
                 created_at: datetime):
        super().__init__(uuid=uuid, name=name, subscriptions_ids=subscriptions_ids,
                         created_at=created_at)
