import json
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class RabbitMQSettings(BaseModel):
    address: IPv4Address
    port: int
    user: str
    password: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "RabbitMQSettings":
        if not Path(config_file_path).exists():
            msg = f"Configuration file not found at {config_file_path}"
            raise FileNotFoundError(msg)

        with open(config_file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        rabbitmq = config["rabbitmq"]
        return RabbitMQSettings(
            address=IPv4Address(rabbitmq["ip_address"]),
            port=rabbitmq["port"],
            user=rabbitmq["user"],
            password=rabbitmq["password"],
        )
