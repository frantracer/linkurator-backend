"""Generate a .env file from .config.json for docker compose."""
import logging
from pathlib import Path

from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.logger import configure_logging

ENV_PATH = Path(__file__).parent.parent / ".env"


def main() -> None:
    settings = ApplicationSettings.from_file()
    configure_logging(settings.logging)

    vpn = settings.vpn

    lines = [
        f"OPENVPN_USER={vpn.openvpn_user}",
        f"OPENVPN_PASSWORD={vpn.openvpn_password}",
        f"VPN_SERVER_COUNTRY={vpn.server_country}",
        f"VPN_HTTP_PROXY_PORT={vpn.http_proxy_port}",
    ]

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    logging.info("Generated %s", ENV_PATH)


if __name__ == "__main__":
    main()
