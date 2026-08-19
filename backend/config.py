import os
from pathlib import Path

from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR}/jobportal.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72

    adzuna_app_id: str = os.getenv("ADZUNA_APP_ID", "")
    adzuna_app_key: str = os.getenv("ADZUNA_APP_KEY", "")
    adzuna_country: str = os.getenv("ADZUNA_COUNTRY", "in")

    rapidapi_key: str = os.getenv("RAPIDAPI_KEY", "")

    default_location: str = os.getenv("DEFAULT_LOCATION", "Bangalore")
    max_users: int = int(os.getenv("MAX_USERS", "2"))

    uploads_dir: Path = ROOT_DIR / "uploads"
    static_dir: Path = ROOT_DIR / "frontend" / "dist"

    class Config:
        env_file = ".env"


settings = Settings()
settings.uploads_dir.mkdir(parents=True, exist_ok=True)

# Railway/Heroku postgres compatibility
if settings.database_url.startswith("postgres://"):
    settings.database_url = settings.database_url.replace("postgres://", "postgresql://", 1)
