import configparser
import os
from ipaddress import IPv4Address

from pydantic import BaseModel


class MongoDBSettings(BaseModel):
    address: IPv4Address
    port: int
    user: str
    password: str
    db_name: str

    @classmethod
    def from_file(cls, config_file_path: str) -> "MongoDBSettings":
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f'Configuration file not found at {config_file_path}')

        config = configparser.ConfigParser()
        config.read(config_file_path)

        return MongoDBSettings(
            address=IPv4Address(config['MONGODB']['ip_address']),
            port=int(config['MONGODB']['port']),
            db_name=config['MONGODB']['database'],
            user=config['MONGODB']['user'],
            password=config['MONGODB']['password']
        )
