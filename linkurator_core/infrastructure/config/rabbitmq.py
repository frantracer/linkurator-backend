from ipaddress import IPv4Address
import os
import configparser


class RabbitMQSettings:
    def __init__(self) -> None:
        config_file_path = './secrets/app_config.ini'

        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f'Configuration file not found at {config_file_path}')

        config = configparser.ConfigParser()
        config.read(config_file_path)

        self.address = IPv4Address(config['RABBITMQ']['ip_address'])
        self.port = int(config['RABBITMQ']['port'])
        self.user = config['RABBITMQ']['user']
        self.password = config['RABBITMQ']['password']
