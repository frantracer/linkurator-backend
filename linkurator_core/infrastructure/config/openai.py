import configparser
import os
from ipaddress import IPv4Address

from pydantic import BaseModel


class OpenAISettings(BaseModel):
    api_key: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "OpenAISettings":
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f'Configuration file not found at {config_file_path}')

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return cls(
            api_key=config['OPENAI']['api_key'],
        )
