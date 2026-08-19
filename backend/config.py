from pathlib import Path

from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{ROOT_DIR}/jobportal.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"

    rapidapi_key: str = ""

    # Apify LinkedIn job scrape (optional — adds many more listings)
    apify_token: str = ""
    apify_enabled: bool = True
    apify_job_actor: str = "harvestapi/linkedin-job-search"
    apify_max_items: int = 25  # per title × location; ~$0.001/job
    apify_posted_limit: str = "Past Month"
    apify_timeout_secs: int = 300

    default_location: str = "Bangalore"
    max_users: int = 3
    min_job_score: float = 40.0

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    uploads_dir: Path = ROOT_DIR / "uploads"
    static_dir: Path = ROOT_DIR / "frontend" / "dist"

    model_config = {"env_file": str(ROOT_DIR / ".env"), "extra": "ignore"}


settings = Settings()
settings.uploads_dir.mkdir(parents=True, exist_ok=True)

# Postgres connection string compatibility (Render/Railway/Heroku)
if settings.database_url.startswith("postgres://"):
    settings.database_url = settings.database_url.replace("postgres://", "postgresql://", 1)
