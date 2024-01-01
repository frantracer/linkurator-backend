from ipaddress import IPv4Address
import os
import configparser


class MongoDBSettings:
    address: IPv4Address
    port: int
    user: str
    password: str
    db_name: str

    def __init__(self) -> None:
        config_file_path = './secrets/app_config.ini'

        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f'Configuration file not found at {config_file_path}')

        config = configparser.ConfigParser()
        config.read(config_file_path)

        self.address = IPv4Address(config['MONGODB']['ip_address'])
        self.port = int(config['MONGODB']['port'])
        self.db_name = config['MONGODB']['database']
        self.user = config['MONGODB']['user']
        self.password = config['MONGODB']['password']
