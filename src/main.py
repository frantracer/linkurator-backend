"""
Main file of the application
"""
import uuid
from http import HTTPStatus
from typing import List, Any
from fastapi import FastAPI
from pydantic import BaseModel, AnyUrl

# Application initialisation
app = FastAPI()


# Output models
class Subscription(BaseModel):
    """
    Information about the different channels the user is subscribed to
    """
    id: uuid.UUID
    name: str


class Item(BaseModel):
    """
    Content item that belongs to a subscription
    """
    id: uuid.UUID
    name: str
    url: AnyUrl
    subscription: Subscription


class Topic(BaseModel):
    """
    Category that includes different subscriptions
    """
    id: uuid.UUID
    name: str
    subscriptions: List[Subscription]


class Message(BaseModel):
    """
    Message with information about the request
    """
    message: str


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
    return []


@app.get("/items",
         response_model=List[Item])
async def items() -> Any:
    """
    Get the items from all of the user subscriptions
    """
    return []


@app.get("/topics",
         response_model=List[Topic])
async def get_all_topics() -> Any:
    """
    Get all the topics from an user
    """
    return []


@app.post("/topics",
          response_model=Topic)
async def create_topic() -> Any:
    """
    Create a new topic for an user
    """
    return Topic()


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
async def assign_subscription_to_topic(topic_id: uuid.UUID, subscription_id: uuid.UUID) -> Any:
    """
    Assign a subscription to a topic
    """
    return Topic(id=topic_id, subscriptions=[Subscription(id=subscription_id)])


@app.delete("/topics/{topic_id}/subscriptions/{subscription_id}",
            response_model=Topic,
            responses={404: {"model": None}})
async def remove_subscription_from_topic(topic_id: uuid.UUID, subscription_id: uuid.UUID) -> Any:
    """
    Remove subscription from topic
    """
    return Topic(id=topic_id, subscriptions=[Subscription(id=subscription_id)])
