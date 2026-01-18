import json
from pathlib import Path
from typing import Any

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

        with open(config_file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        api = config["api"]
        return cls(
            host=api["host"],
            port=api["port"],
            workers=api["workers"],
            debug=api["debug"],
            reload=api["reload"],
            with_gunicorn=api["with_gunicorn"],
        )
