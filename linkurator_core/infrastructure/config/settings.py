import json
from enum import StrEnum
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from pydantic import AnyUrl, BaseModel, model_validator

DEFAULT_CONFIG_FILENAME = ".config.json"


class ApiSettings(BaseModel):
    host: str
    port: int
    workers: int
    debug: bool
    reload: bool
    with_gunicorn: bool


class AIAgentSettings(BaseModel):
    base_url: str


class GoogleWebCredentials(BaseModel):
    client_id: str
    project_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_secret: str
    redirect_uris: list[str]
    javascript_origins: list[str]


class GoogleOAuth(BaseModel):
    web: GoogleWebCredentials


class GoogleSettings(BaseModel):
    gemini_api_key: str
    youtube_api_keys: list[str]
    oauth: GoogleOAuth
    email_service_credentials: dict[str, str]
    service_account_email: str


class SpotifyCredentialPair(BaseModel):
    client_id: str
    client_secret: str


class SpotifySettings(BaseModel):
    credentials: list[SpotifyCredentialPair]

    @model_validator(mode="after")
    def check_credentials_not_empty(self) -> "SpotifySettings":
        if len(self.credentials) == 0:
            msg = "At least one Spotify credential pair must be provided."
            raise ValueError(msg)
        return self


class PatreonSettings(BaseModel):
    client_id: str
    client_secret: str
    refresh_token: str


class MongoDBSettings(BaseModel):
    ip_address: IPv4Address
    port: int
    user: str
    password: str
    database: str


class RabbitMQSettings(BaseModel):
    ip_address: IPv4Address
    port: int
    user: str
    password: str


class LogfireEnvironment(StrEnum):
    PROD = "prod"
    DEV = "dev"
    TEST = "test"


class LogfireSettings(BaseModel):
    enabled: bool
    token: str
    environment: LogfireEnvironment


class LogSettings(BaseModel):
    level: str
    logfire: LogfireSettings


class WebsiteSettings(BaseModel):
    host: AnyUrl
    valid_domains: list[str]


class ApplicationSettings(BaseModel):
    """
    Settings for the application.
    """

    api: ApiSettings
    ai_agent: AIAgentSettings
    google: GoogleSettings
    spotify: SpotifySettings
    patreon: PatreonSettings | None
    mongodb: MongoDBSettings
    rabbitmq: RabbitMQSettings
    logging: LogSettings
    website: WebsiteSettings

    @classmethod
    def from_file(cls, file_path: str = DEFAULT_CONFIG_FILENAME) -> "ApplicationSettings":
        if not Path(file_path).exists():
            msg = f"Configuration file not found at {file_path}"
            raise FileNotFoundError(msg)

        with open(file_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

        patreon_config = config.get("patreon")
        patreon_settings = PatreonSettings(**patreon_config) if patreon_config else None

        return cls(
            api=ApiSettings(**config["api"]),
            ai_agent=AIAgentSettings(**config["ai_agent"]),
            google=GoogleSettings(**config["google"]),
            spotify=SpotifySettings(**config["spotify"]),
            patreon=patreon_settings,
            mongodb=MongoDBSettings(**config["mongodb"]),
            rabbitmq=RabbitMQSettings(**config["rabbitmq"]),
            logging=LogSettings(**config["logging"]),
            website=WebsiteSettings(**config["website"]),
        )
