import json
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class MongoDBSettings(BaseModel):
    address: IPv4Address
    port: int
    user: str
    password: str
    db_name: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "MongoDBSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        with open(config_file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        mongodb = config["mongodb"]
        return MongoDBSettings(
            address=IPv4Address(mongodb["ip_address"]),
            port=mongodb["port"],
            db_name=mongodb["database"],
            user=mongodb["user"],
            password=mongodb["password"],
        )
