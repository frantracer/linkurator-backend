import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class EnvSettings(BaseModel):
    GOOGLE_SECRET_PATH: str = os.getenv('LINKURATOR_GOOGLE_SECRET_PATH', "secrets/client_secret.json")
    WEBSITE_URL: str = os.getenv('LINKURATOR_WEBSITE_URL', "https://linkurator.com")
    VALIDATE_EMAIL_URL: str = os.getenv('LINKURATOR_VALIDATE_EMAIL_URL', "https://linkurator.com/validate_email")
