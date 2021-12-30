"""
Main file of the application
"""
from datetime import datetime
from uuid import UUID, uuid4
from http import HTTPStatus
from typing import List, Any
from fastapi import FastAPI
from pydantic import BaseModel, AnyUrl
from pydantic.tools import parse_obj_as

# Application initialisation
app = FastAPI()


# Output models
class Topic(BaseModel):
    """
    Category that includes different subscriptions
    """
    uuid: UUID
    name: str
    subscriptions_ids: List[UUID]

    def __init__(self, uuid: UUID, name: str, subscriptions_ids: List[UUID]):
        super().__init__(uuid=uuid, name=name, subscriptions_ids=subscriptions_ids)


class Subscription(BaseModel):
    """
    Information about the different channels the user is subscribed to
    """
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    last_update: datetime

    def __init__(self, uuid: UUID, name: str,
                 url: AnyUrl, thumbnail: AnyUrl, last_update: datetime):
        super().__init__(uuid=uuid, name=name,
                         url=url, thumbnail=thumbnail, last_update=last_update)


class Item(BaseModel):
    """
    Content item that belongs to a subscription
    """
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl

    def __init__(self, uuid: UUID, name: str, url: AnyUrl, thumbnail: AnyUrl):
        super().__init__(uuid=uuid, name=name, url=url, thumbnail=thumbnail)


class Message(BaseModel):
    """
    Message with information about the request
    """
    message: str

    def __init__(self, message: str):
        super().__init__(message=message)


# Endpoints definition
@app.get("/health")
async def health() -> None:
    """
    Health endpoint returns a 200 if the service is alive
    """
    return


@app.get("/subscriptions",
         response_model=List[Subscription])
async def get_all_subscriptions() -> Any:
    """
    Get the list of the user subscriptions
    """
    # Initialize dummy subscription
    subscription = Subscription(
        uuid=uuid4(),
        name="Dummy",
        url=parse_obj_as(AnyUrl, "https://www.youtube.com/channel/UC-9-kyTW8ZkZNDHQJ6FgpwQ"),
        thumbnail=parse_obj_as(AnyUrl, "https://i.ytimg.com/vi/tntOCGkgt98/maxresdefault.jpg"),
        last_update=datetime.now()
    )

    return [subscription]


@app.get("/topics/{topic_id}/items",
         response_model=List[Item])
async def items_by_topic() -> Any:
    """
    Get the items from a topic
    """
    return []


@app.get("/topics",
         response_model=List[Topic])
async def get_all_topics() -> Any:
    """
    Get all the topics from a user
    """
    return []


@app.post("/topics",
          response_model=Topic)
async def create_topic() -> Any:
    """
    Create a new topic for an user
    """
    return Topic(
        uuid=uuid4(),
        name="Dummy",
        subscriptions_ids=[]
    )


@app.delete("/topics/{topic_id}",
            status_code=HTTPStatus.NO_CONTENT,
            responses={404: {"model": None}})
async def delete_topic() -> Any:
    """
    Delete a topic
    """
    return


@app.post("/topics/{topic_id}/subscriptions/{subscription_id}",
          response_model=Topic,
          responses={404: {"model": Message}})
async def assign_subscription_to_topic(topic_id: UUID, subscription_id: UUID) -> Any:
    """
    Assign a subscription to a topic
    """
    return Topic(
        uuid=topic_id,
        name="Dummy",
        subscriptions_ids=[subscription_id]
    )


@app.delete("/topics/{topic_id}/subscriptions/{subscription_id}",
            response_model=Topic,
            responses={404: {"model": None}})
async def remove_subscription_from_topic(topic_id: UUID, subscription_id: UUID) -> Any:
    """
    Remove subscription from topic
    """
    return Topic(
        uuid=topic_id,
        name="Dummy",
        subscriptions_ids=[subscription_id]
    )
