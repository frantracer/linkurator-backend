import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class LogfireEnvironment(StrEnum):
    PROD = "prod"
    DEV = "dev"
    TEST = "test"


class LogSettings(BaseModel):
    level: str
    logfire_enabled: bool
    logfire_token: str
    logfire_environment: LogfireEnvironment

    @classmethod
    def from_file(cls, config_path: str) -> "LogSettings":
        if not Path(config_path).exists():
            msg = f"Configuration file not found at {config_path}"
            raise FileNotFoundError(msg)

        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        logging = config.get("logging", {})
        logfire = config.get("logfire", {})

        return cls(
            level=logging.get("level", "INFO"),
            logfire_enabled=logfire.get("enabled", False),
            logfire_token=logfire.get("token", ""),
            logfire_environment=LogfireEnvironment(logfire.get("environment", LogfireEnvironment.DEV)),
        )
