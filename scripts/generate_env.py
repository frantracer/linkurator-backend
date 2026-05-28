"""Generate a .env file from .config.json for docker compose."""
import logging
from pathlib import Path

from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.logger import configure_logging

ENV_PATH = Path(__file__).parent.parent / ".env"


def main() -> None:
    settings = ApplicationSettings.from_file()
    configure_logging(settings.logging)

    mongodb = settings.mongodb
    rabbitmq = settings.rabbitmq
    vpn = settings.vpn

    values: dict[str, str] = {
        "MONGODB_USER": mongodb.user,
        "MONGODB_PASS": mongodb.password,
        "MONGODB_PORT": str(mongodb.port),
        "RABBITMQ_USER": rabbitmq.user,
        "RABBITMQ_PASS": rabbitmq.password,
        "RABBITMQ_PORT": str(rabbitmq.port),
        "VPN_PROFILE": "infra" if vpn.enabled else "vpn-disabled",
        "OPENVPN_USER": vpn.openvpn_user,
        "OPENVPN_PASSWORD": vpn.openvpn_password,
        "VPN_SERVER_COUNTRY": vpn.server_country,
        "VPN_HTTP_PROXY_PORT": str(vpn.http_proxy_port),
    }

    lines = [f"{k}={v}" for k, v in values.items()]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    logging.info("Generated %s", ENV_PATH)


if __name__ == "__main__":
    main()
