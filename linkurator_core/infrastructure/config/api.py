import configparser
from pathlib import Path

from pydantic import BaseModel


class ApiSettings(BaseModel):
    host: str
    port: int
    workers: int
    debug: bool
    reload: bool
    with_gunicorn: bool

    @classmethod
    def from_file(cls, config_file_path: str) -> "ApiSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return cls(
            host=config["API"]["host"],
            port=config.getint("API", "port"),
            workers=config.getint("API", "workers"),
            debug=config.getboolean("API", "debug"),
            reload=config.getboolean("API", "reload"),
            with_gunicorn=config.getboolean("API", "with_gunicorn"),
        )
