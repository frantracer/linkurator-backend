import configparser
from enum import StrEnum

from pydantic import BaseModel


class LogfireEnvironment(StrEnum):
    PROD = 'prod'
    DEV = 'dev'


class LogSettings(BaseModel):
    level: str
    logfire_enabled: bool
    logfire_token: str
    logfire_environment: LogfireEnvironment

    @classmethod
    def from_file(cls, config_path: str) -> "LogSettings":
        config = configparser.ConfigParser()
        config.read(config_path)

        return cls(
            level=config.get('LOGGING', 'level', fallback='INFO'),
            logfire_enabled=config.getboolean('LOGFIRE', 'enabled', fallback=False),
            logfire_token=config.get('LOGFIRE', 'token', fallback=''),
            logfire_environment=LogfireEnvironment(config.get('LOGFIRE', 'environment', fallback=LogfireEnvironment.DEV)),
        )
