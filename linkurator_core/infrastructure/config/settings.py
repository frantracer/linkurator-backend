from pydantic import BaseModel

from linkurator_core.infrastructure.config.ai_agent import AIAgentSettings
from linkurator_core.infrastructure.config.api import ApiSettings
from linkurator_core.infrastructure.config.google import GoogleSettings
from linkurator_core.infrastructure.config.log import LogSettings
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.config.rabbitmq import RabbitMQSettings
from linkurator_core.infrastructure.config.spotify import SpotifyClientSecrets
from linkurator_core.infrastructure.config.website import WebsiteSettings

DEFAULT_CONFIG_FILENAME = ".config.json"


class ApplicationSettings(BaseModel):
    """
    Settings for the application.
    """

    api: ApiSettings
    ai_agent: AIAgentSettings
    google: GoogleSettings
    spotify: SpotifyClientSecrets
    mongodb: MongoDBSettings
    rabbitmq: RabbitMQSettings
    log: LogSettings
    website: WebsiteSettings

    @classmethod
    def from_file(cls, file_path: str = DEFAULT_CONFIG_FILENAME) -> "ApplicationSettings":
        return cls(
            api=ApiSettings.from_file(file_path),
            ai_agent=AIAgentSettings.from_file(file_path),
            google=GoogleSettings.from_file(file_path),
            spotify=SpotifyClientSecrets.from_file(file_path),
            mongodb=MongoDBSettings.from_file(file_path),
            rabbitmq=RabbitMQSettings.from_file(file_path),
            log=LogSettings.from_file(file_path),
            website=WebsiteSettings.from_file(file_path),
        )
