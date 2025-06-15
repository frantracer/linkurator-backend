from __future__ import annotations

from pydantic import BaseModel

from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class ExternalCredentialSchema(BaseModel):
    """Profile with the user information."""

    credential_type: ExternalServiceType
    credential_value: str
    created_at: Iso8601Datetime

    @classmethod
    def from_domain_credential(cls, credential: ExternalServiceCredential) -> ExternalCredentialSchema:
        return cls(
            credential_type=credential.credential_type,
            credential_value=credential.credential_value,
            created_at=credential.created_at,
        )
