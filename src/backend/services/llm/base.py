from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypedDict

import httpx


class ChatMessage(TypedDict):
    role: str  # user | assistant | system
    content: str


class LLMError(Exception):
    ...


class LLMProvider(ABC):
    """Единый интерфейс LLM-провайдера"""
    
    name: str = "base"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

        # transport для тестов
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        """Заголовки по умолчанию (переопределяется провайдером)."""
        return {}

    def _client(self, *, streaming: bool = False) -> httpx.AsyncClient:
        timeout = (
            httpx.Timeout(self.timeout, read=None)
            if streaming
            else httpx.Timeout(self.timeout)
        )
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
            transport=self._transport,
        )

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> str:
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...
