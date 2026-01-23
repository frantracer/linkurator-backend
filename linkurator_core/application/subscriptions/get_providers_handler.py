from dataclasses import dataclass

from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


@dataclass
class Provider:
    name: str
    alias: str
    thumbnail: str


class GetProvidersHandler:
    def __init__(self, subscription_services: list[SubscriptionService]) -> None:
        self.subscription_services = subscription_services

    def handle(self) -> list[Provider]:
        return [
            Provider(
                name=service.provider_name(),
                alias=service.provider_alias(),
                thumbnail=service.provider_thumbnail(),
            )
            for service in self.subscription_services
        ]
