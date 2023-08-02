from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from linkurator_core.domain.users.external_service_credential import ExternalServiceType, ExternalServiceCredential


class ExternalCredentialSchema(BaseModel):
    """
    Profile with the user information
    """
    credential_type: ExternalServiceType
    credential_value: str
    created_at: datetime

    @classmethod
    def from_domain_credential(cls, credential: ExternalServiceCredential) -> ExternalCredentialSchema:
        return cls(
            credential_type=credential.credential_type,
            credential_value=credential.credential_value,
            created_at=credential.created_at
        )
