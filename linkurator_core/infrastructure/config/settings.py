from pydantic import BaseModel

from linkurator_core.infrastructure.config.env_settings import EnvSettings
from linkurator_core.infrastructure.config.google import GoogleSettings
from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets, SpotifyClientSecrets
from linkurator_core.infrastructure.config.log import LogSettings
from linkurator_core.infrastructure.config.mongodb import MongoDBSettings
from linkurator_core.infrastructure.config.rabbitmq import RabbitMQSettings

DEFAULT_CONFIG_FILENAME = ".config.ini"


class ApplicationSettings(BaseModel):
    """
    Settings for the application.
    """

    env: EnvSettings
    google: GoogleClientSecrets
    spotify: SpotifyClientSecrets
    mongodb: MongoDBSettings
    rabbitmq: RabbitMQSettings
    log: LogSettings
    google_ai: GoogleSettings

    @classmethod
    def from_file(cls, file_path: str = DEFAULT_CONFIG_FILENAME) -> "ApplicationSettings":
        return cls(
            env=EnvSettings(),
            google=GoogleClientSecrets.from_file(),
            spotify=SpotifyClientSecrets.from_file(),
            mongodb=MongoDBSettings.from_file(file_path),
            rabbitmq=RabbitMQSettings.from_file(file_path),
            log=LogSettings.from_file(file_path),
            google_ai=GoogleSettings.from_file(file_path),
        )
