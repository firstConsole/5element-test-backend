from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class LLMSettings(BaseModel):
    """Настройки LLM-провайдера"""

    provider: Literal["ollama", "openai"] = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    api_key: str = ""
    timeout: float = 60.0


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
    access_token_expire_minutes: int = 60 * 24

    # LLM
    llm_config_path: str = "config/llm.yaml"
    llm_api_key: str = ""
    llm: LLMSettings = LLMSettings()


def _load_llm_settings(config_path: str, api_key_override: str) -> LLMSettings:
    """Прочитать настройки LLM из YAML и наложить api_key из окружения
    Если файла нет — используются значения по умолчанию LLMSettings
    """
    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    data: dict = {}
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict):
            data = raw.get("llm", raw)

    if api_key_override:
        data["api_key"] = api_key_override

    return LLMSettings(**data)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()  # type: ignore[call-arg]
    settings.llm = _load_llm_settings(settings.llm_config_path, settings.llm_api_key)
    return settings
