from pydantic import BaseModel

from linkurator_core.infrastructure.config.ai_agent import AIAgentSettings
from linkurator_core.infrastructure.config.api import ApiSettings
from linkurator_core.infrastructure.config.google import GoogleSettings
from linkurator_core.infrastructure.config.log import LogSettings
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.config.rabbitmq import RabbitMQSettings
from linkurator_core.infrastructure.config.secrets import GoogleClientSecrets, SpotifyClientSecrets
from linkurator_core.infrastructure.config.secrets_settings import SecretsSettings

DEFAULT_CONFIG_FILENAME = ".config.json"


class ApplicationSettings(BaseModel):
    """
    Settings for the application.
    """

    secrets: SecretsSettings
    api: ApiSettings
    ai_agent: AIAgentSettings
    google: GoogleClientSecrets
    spotify: SpotifyClientSecrets
    mongodb: MongoDBSettings
    rabbitmq: RabbitMQSettings
    log: LogSettings
    google_ai: GoogleSettings

    @classmethod
    def from_file(cls, file_path: str = DEFAULT_CONFIG_FILENAME) -> "ApplicationSettings":
        return cls(
            secrets=SecretsSettings.from_file(file_path),
            api=ApiSettings.from_file(file_path),
            ai_agent=AIAgentSettings.from_file(file_path),
            google=GoogleClientSecrets.from_file(),
            spotify=SpotifyClientSecrets.from_file(),
            mongodb=MongoDBSettings.from_file(file_path),
            rabbitmq=RabbitMQSettings.from_file(file_path),
            log=LogSettings.from_file(file_path),
            google_ai=GoogleSettings.from_file(file_path),
        )
