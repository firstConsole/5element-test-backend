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


class OllamaProvider(LLMProvider):
    """Провайдер для Ollama"""

    name = "ollama"

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
                resp = await client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Ollama вернул {exc.response.status_code}: {exc.response.text}"
            ) from exc
        
        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось связаться с Ollama: {exc}") from exc

        return data.get("message", {}).get("content", "")

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
                async with client.stream("POST", "/api/chat", json=payload) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode(errors="replace")
                        raise LLMError(f"Ollama вернул {resp.status_code}: {body}")
                    
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        piece = chunk.get("message", {}).get("content", "")

                        if piece:
                            yield piece

                        if chunk.get("done"):
                            break

        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось связаться с Ollama: {exc}") from exc

    async def list_models(self) -> list[str]:
        try:
            async with self._client() as client:
                resp = await client.get("/api/tags")
                resp.raise_for_status()
                data = resp.json()
                
        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось получить список моделей Ollama: {exc}") from exc

        return [m["name"] for m in data.get("models", []) if "name" in m]

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
                resp = await client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Ollama вернул {exc.response.status_code}: {exc.response.text}"
            ) from exc
        
        except httpx.HTTPError as exc:
            raise LLMError(f"Не удалось связаться с Ollama: {exc}") from exc

        message = data.get("message", {})
        tool_calls = []

        for i, call in enumerate(message.get("tool_calls") or []):
            fn = call.get("function", {})
            arguments = fn.get("arguments") or {}

            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            tool_calls.append(
                ToolCall(id=str(i), name=fn.get("name", ""), arguments=arguments)
            )

        return ChatResult(content=message.get("content") or "", tool_calls=tool_calls)

    def format_assistant_tool_calls(self, result: ChatResult) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": result.content or "",
            "tool_calls": [
                {"function": {"name": tc.name, "arguments": tc.arguments}}
                for tc in result.tool_calls
            ],
        }

    def format_tool_result(self, call: ToolCall, output: str) -> dict[str, Any]:
        return {"role": "tool", "content": output}
