from pydantic import BaseModel
from ipaddress import IPv4Address
import os
import configparser


class RabbitMQSettings(BaseModel):
    address: IPv4Address
    port: int
    user: str
    password: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "RabbitMQSettings":
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f'Configuration file not found at {config_file_path}')

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return RabbitMQSettings(
            address=IPv4Address(config['RABBITMQ']['ip_address']),
            port=int(config['RABBITMQ']['port']),
            user=config['RABBITMQ']['user'],
            password=config['RABBITMQ']['password']
        )
