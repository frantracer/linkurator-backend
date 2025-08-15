import configparser
from ipaddress import IPv4Address
from pathlib import Path

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

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return RabbitMQSettings(
            address=IPv4Address(config["RABBITMQ"]["ip_address"]),
            port=int(config["RABBITMQ"]["port"]),
            user=config["RABBITMQ"]["user"],
            password=config["RABBITMQ"]["password"],
        )
