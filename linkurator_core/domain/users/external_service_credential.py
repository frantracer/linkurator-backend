from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class ExternalServiceType(Enum):
    YOUTUBE_API_KEY = 'youtube_api_key'
    OPENAI_API_KEY = 'openai_api_key'


@dataclass
class ExternalServiceCredential:
    user_id: UUID
    credential_type: ExternalServiceType
    credential_value: str
    created_at: datetime
    updated_at: datetime

    def set_credential(self, value: str) -> None:
        self.credential_value = value
        self.updated_at = datetime.utcnow()
