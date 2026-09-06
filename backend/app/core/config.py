"""Application configuration loaded from environment variables / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Backend directory: the folder that contains app/core/config.py is backend/app/core,
# so the backend root is two levels up.
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "wastewise"
    nvidia_api_key: str = ""
    nim_model: str = "meta/llama-3.2-11b-vision-instruct"
    nim_endpoint: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    nim_timeout_seconds: float = 180.0
    jwt_secret: str = "change_this_to_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    upload_dir: str = str(BACKEND_DIR / "app" / "static_uploads")


settings = Settings()
