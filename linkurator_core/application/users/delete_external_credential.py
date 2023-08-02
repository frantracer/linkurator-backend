from uuid import UUID

from linkurator_core.domain.users.external_service_credential import ExternalServiceType
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository


class DeleteExternalCredentialHandler:
    def __init__(self, credentials_repository: ExternalCredentialRepository):
        self.credentials_repository = credentials_repository

    async def handle(self, user_uuid: UUID, credential_type: ExternalServiceType, credential_value: str) -> None:
        await self.credentials_repository.delete(user_uuid, credential_type, credential_value)
