import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class AIAgentSettings(BaseModel):
    base_url: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "AIAgentSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        with open(config_file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        return cls(
            base_url=config["ai_agent"]["base_url"],
        )
