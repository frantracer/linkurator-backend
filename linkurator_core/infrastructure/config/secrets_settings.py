import configparser
from pathlib import Path

from pydantic import AnyUrl, BaseModel


class SecretsSettings(BaseModel):
    google_secret_path: str
    google_youtube_secret_path: str
    spotify_secret_path: str
    website_url: AnyUrl
    valid_domains: list[str]
    google_service_account_email: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "SecretsSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return cls(
            google_secret_path=config["SECRETS"]["google_secret_path"],
            google_youtube_secret_path=config["SECRETS"]["google_youtube_secret_path"],
            spotify_secret_path=config["SECRETS"]["spotify_secret_path"],
            website_url=AnyUrl(config["WEBSITE"]["host"]),
            valid_domains=config["WEBSITE"]["valid_domains"].split(","),
            google_service_account_email=config["GOOGLE"]["service_account_email"],
        )
