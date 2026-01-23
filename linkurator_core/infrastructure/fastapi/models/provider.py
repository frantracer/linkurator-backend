from __future__ import annotations

from pydantic import AnyUrl, BaseModel

from linkurator_core.application.subscriptions.get_providers_handler import Provider


class ProviderSchema(BaseModel):
    """Information about a subscription provider."""

    name: str
    alias: str
    thumbnail: AnyUrl

    @classmethod
    def from_domain_provider(cls, provider: Provider) -> ProviderSchema:
        return cls(
            name=provider.name,
            alias=provider.alias,
            thumbnail=AnyUrl(provider.thumbnail),
        )
