"""
Main file of the application
"""
from dataclasses import dataclass

from fastapi.applications import FastAPI

from linkurator_core.infrastructure.fastapi.routers import authentication
from linkurator_core.infrastructure.fastapi.routers import subscriptions, topics

# FastAPI application
app: FastAPI = FastAPI()


# Endpoints definition
@dataclass
class Handlers:
    message: str = "Hello world!"


def create_app(handlers: Handlers) -> FastAPI:
    """
    Create the application
    """

    api = FastAPI()

    @api.get("/health")
    async def health() -> str:
        """
        Health endpoint returns a 200 if the service is alive
        """
        return handlers.message

    api.include_router(authentication.get_router())
    api.include_router(topics.get_router(), prefix="/topics")
    api.include_router(subscriptions.get_router(), prefix="/subscriptions")

    return api
