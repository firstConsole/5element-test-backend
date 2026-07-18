from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, TypedDict

import httpx


class ChatMessage(TypedDict):
    role: str  # user | assistant | system
    content: str


class LLMError(Exception):
    ...


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResult:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    """Интерфейс LLM-провайдера"""
    
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

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult:
        raise LLMError(f"Провайдер {self.name} не поддерживает tool calling")

    def format_assistant_tool_calls(self, result: ChatResult) -> dict[str, Any]:
        """Сообщение ассистента с запросами вызовов (OpenAI-совместимый формат)."""
        return {
            "role": "assistant",
            "content": result.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in result.tool_calls
            ],
        }

    def format_tool_result(self, call: ToolCall, output: str) -> dict[str, Any]:
        return {"role": "tool", 
                "tool_call_id": call.id, 
                "content": output}
