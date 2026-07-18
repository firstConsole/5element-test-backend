from __future__ import annotations

from backend.core.config import Settings, get_settings
from backend.services.llm.base import LLMError, LLMProvider
from backend.services.llm.ollama import OllamaProvider
from backend.services.llm.openai import OpenAIProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
}


def get_provider(settings: Settings | None = None) -> LLMProvider:
    """Собрать LLM-провайдера по конфигурации приложения."""
    cfg = (settings or get_settings()).llm
    provider_cls = _PROVIDERS.get(cfg.provider)
    if provider_cls is None:
        raise LLMError(
            f"Неизвестный LLM-провайдер: {cfg.provider!r}. "
            f"Доступны: {', '.join(_PROVIDERS)}"
        )
    return provider_cls(
        base_url=cfg.base_url,
        model=cfg.model,
        api_key=cfg.api_key,
        timeout=cfg.timeout,
    )


def get_llm_provider() -> LLMProvider:
    return get_provider()
