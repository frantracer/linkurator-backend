from __future__ import annotations

from fastapi import status
from fastapi.routing import APIRouter

from linkurator_core.application.subscriptions.get_providers_handler import GetProvidersHandler
from linkurator_core.infrastructure.fastapi.models.provider import ProviderSchema


def get_router(
    get_providers_handler: GetProvidersHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/",
        status_code=status.HTTP_200_OK,
    )
    async def get_providers() -> list[ProviderSchema]:
        """Get list of available subscription providers."""
        providers = get_providers_handler.handle()
        return [ProviderSchema.from_domain_provider(provider) for provider in providers]

    return router
