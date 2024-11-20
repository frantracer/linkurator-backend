import os

from dotenv import load_dotenv
from pydantic import BaseModel, AnyUrl

load_dotenv()

DEFAULT_DOMAINS = "linkurator.com,api.linkurator.com,www.linkurator.com"


class EnvSettings(BaseModel):
    GOOGLE_SECRET_PATH: str = os.getenv('LINKURATOR_GOOGLE_SECRET_PATH', "secrets/client_secret.json")
    WEBSITE_URL: AnyUrl = AnyUrl(os.getenv('LINKURATOR_WEBSITE_URL', "https://linkurator.com"))
    VALID_DOMAINS: list[str] = os.getenv('LINKURATOR_VALID_DOMAINS', DEFAULT_DOMAINS).split(",")

    GOOGLE_SERVICE_ACCOUNT_EMAIL: str = os.getenv("LINKURATOR_GOOGLE_SERVICE_ACCOUNT_EMAIL", "admin@linkurator.com")
