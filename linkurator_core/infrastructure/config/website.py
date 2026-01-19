import json
from typing import Any

from pydantic import AnyUrl, BaseModel


class WebsiteSettings(BaseModel):
    website_url: AnyUrl
    valid_domains: list[str]

    @classmethod
    def from_file(cls, config_file_path: str) -> "WebsiteSettings":
        with open(config_file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        website = config["website"]

        return cls(
            website_url=AnyUrl(website["host"]),
            valid_domains=website["valid_domains"],
        )
