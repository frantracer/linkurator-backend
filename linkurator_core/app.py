"""
Main file of the application
"""
import logging
from typing import Optional

from fastapi.applications import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from linkurator_core.app_handlers import app_handlers, Handlers
from linkurator_core.common.domain.session import Session
from linkurator_core.items.infrastructure.fastapi import items_routes
from linkurator_core.subscriptions.infrastructure.fastapi import subscriptions_routes
from linkurator_core.topics.infrastructure.fastapi import topics_routes
from linkurator_core.users.infrastructure.fastapi import profile_routes, authentication_routes


def create_app() -> FastAPI:
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                        level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
    return create_app_from_handlers(app_handlers())


def create_app_from_handlers(handlers: Handlers) -> FastAPI:
    app = FastAPI()

    async def get_current_session(request: Request) -> Optional[Session]:
        token = request.cookies.get("token")
        if token is None:
            return None
        session = handlers.validate_token.handle(access_token=token, refresh_token=None)
        return session

    @app.get("/health")
    async def health() -> str:
        """
        Health endpoint returns a 200 if the service is alive
        """
        return "OK"

    app.include_router(
        authentication_routes.get_router(
            validate_token_handler=handlers.validate_token,
            google_client=handlers.google_client
        )
    )
    app.include_router(
        profile_routes.get_router(
            get_session=get_current_session,
            get_user_profile_handler=handlers.get_user_profile_handler
        )
    )
    app.include_router(
        topics_routes.get_router(
            get_session=get_current_session,
            create_topic_handler=handlers.create_topic_handler,
            get_topic_handler=handlers.get_topic_handler,
            get_user_topics_handler=handlers.get_user_topics_handler,
            assign_subscription_to_user_topic_handler=handlers.assign_subscription_to_topic_handler,
            unassign_subscription_from_user_topic_handler=handlers.unassign_subscription_from_topic_handler,
            delete_user_topic_handler=handlers.delete_topic_handler,
            update_user_topic_handler=handlers.update_topic_handler
        )
    )
    app.include_router(
        subscriptions_routes.get_router(
            get_session=get_current_session,
            get_user_subscriptions_handler=handlers.get_user_subscriptions,
            delete_subscription_items_handler=handlers.delete_subscription_items_handler
        ),
    )
    app.include_router(
        items_routes.get_router(
            get_session=get_current_session,
            get_item_handler=handlers.get_item_handler,
            create_item_interaction_handler=handlers.create_item_interaction_handler,
            delete_item_interaction_handler=handlers.delete_item_interaction_handler,
            get_topic_items_handler=handlers.get_topic_items_handler,
            get_subscription_items_handler=handlers.get_subscription_items_handler,
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    return app
