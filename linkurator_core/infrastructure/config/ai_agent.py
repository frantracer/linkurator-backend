import configparser
from pathlib import Path

from pydantic import BaseModel


class AIAgentSettings(BaseModel):
    base_url: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "AIAgentSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return cls(
            base_url=config["AIAGENT"]["base_url"],
        )
