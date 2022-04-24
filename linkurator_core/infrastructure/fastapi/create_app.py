"""
Main file of the application
"""
from dataclasses import dataclass

from fastapi.applications import FastAPI

from linkurator_core.application.register_user_handler import RegisterUserHandler
from linkurator_core.application.validate_token_handler import ValidateTokenHandler
from linkurator_core.infrastructure.fastapi.routers import authentication, subscriptions, topics
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


@dataclass
class Handlers:
    register_user: RegisterUserHandler
    validate_token: ValidateTokenHandler
    google_client: GoogleAccountService


def create_app(handlers: Handlers) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health() -> str:
        """
        Health endpoint returns a 200 if the service is alive
        """
        return "OK"

    app.include_router(authentication.get_router(
        validate_token_handler=handlers.validate_token,
        register_user_handler=handlers.register_user,
        google_client=handlers.google_client))
    app.include_router(topics.get_router(), prefix="/topics")
    app.include_router(subscriptions.get_router(), prefix="/subscriptions")

    return app
