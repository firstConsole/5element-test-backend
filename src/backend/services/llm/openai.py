from __future__ import annotations

import json
import httpx

from collections.abc import AsyncIterator

from typing import Any

from backend.services.llm.base import (
    ChatMessage,
    ChatResult,
    LLMError,
    LLMProvider,
    ToolCall,
)


class OpenAIProvider(LLMProvider):
    """Провайдер для OpenAI-совместимого API"""

    name = "openai"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> str:
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            async with self._client() as client:
                resp = await client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"OpenAI API вернул {exc.response.status_code}: {exc.response.text}"
            ) from exc
        
        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось связаться с OpenAI API: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Неожиданный ответ OpenAI API: {data}") from exc

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
        }
        try:
            async with self._client(streaming=True) as client:
                async with client.stream(
                    "POST", "/chat/completions", json=payload
                ) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode(errors="replace")
                        raise LLMError(f"OpenAI API вернул {resp.status_code}: {body}")
                    
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue

                        data = line[len("data:"):].strip()

                        if data == "[DONE]":
                            break

                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content")

                        if delta:
                            yield delta

        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось связаться с OpenAI API: {exc}") from exc

    async def list_models(self) -> list[str]:
        try:
            async with self._client() as client:
                resp = await client.get("/models")
                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось получить список моделей OpenAI API: {exc}") from exc

        return [m["id"] for m in data.get("data", []) if "id" in m]

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            async with self._client() as client:
                resp = await client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"OpenAI API вернул {exc.response.status_code}: {exc.response.text}"
            ) from exc
        
        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось связаться с OpenAI API: {exc}") from exc

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Неожиданный ответ OpenAI API: {data}") from exc

        tool_calls = []

        for call in message.get("tool_calls") or []:
            fn = call.get("function", {})
            raw_args = fn.get("arguments") or "{}"
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            tool_calls.append(
                ToolCall(id=call.get("id", ""), name=fn.get("name", ""), arguments=arguments)
            )

        return ChatResult(content=message.get("content") or "", tool_calls=tool_calls)
