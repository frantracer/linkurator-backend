import json
from pathlib import Path
from typing import Any

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

        with open(config_file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        secrets = config["secrets"]
        website = config["website"]
        google = config["google"]

        return cls(
            google_secret_path=secrets["google_secret_path"],
            google_youtube_secret_path=secrets["google_youtube_secret_path"],
            spotify_secret_path=secrets["spotify_secret_path"],
            website_url=AnyUrl(website["host"]),
            valid_domains=website["valid_domains"],
            google_service_account_email=google["service_account_email"],
        )
