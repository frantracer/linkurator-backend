import configparser
from pathlib import Path

from pydantic import BaseModel


class GoogleSettings(BaseModel):
    api_key: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "GoogleSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return cls(
            api_key=config["GOOGLE"]["api_key"],
        )
