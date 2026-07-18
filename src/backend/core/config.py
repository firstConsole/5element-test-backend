from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = "API Chat"
    app_description: str = "API Chat for 5 Element test task"
    app_version: str = "0.0.1"
    app_environment: str = "dev"
    app_debug: bool = True

    # Database
    database_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() # type: ignore[call-arg]