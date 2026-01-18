import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class GoogleSettings(BaseModel):
    gemini_api_key: str
    youtube_api_keys: list[str]

    @classmethod
    def from_file(cls, config_file_path: str) -> "GoogleSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        with open(config_file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        google = config["google"]
        return cls(
            gemini_api_key=google["gemini_api_key"],
            youtube_api_keys=google["youtube_api_keys"],
        )
