import json

import httpx
import pytest

from backend.services.llm import (
    LLMError,
    OllamaProvider,
    OpenAIProvider,
    default_registry,
    run_with_tools,
)
from backend.services.llm.tools.builtin import CalculateTool


# ---- инструменты ----

async def test_calculate_tool():
    calc = CalculateTool()
    assert await calc.run({"expression": "2 + 2 * 10"}) == "22"
    assert await calc.run({"expression": "(3 + 4) * 2"}) == "14"
    # небезопасное выражение отклоняется, а не выполняется
    assert "Ошибка" in await calc.run({"expression": "__import__('os')"})


# ---- Ollama ----

def _ollama_handler(req: httpx.Request) -> httpx.Response:
    if req.url.path == "/api/tags":
        return httpx.Response(200, json={"models": [{"name": "llama3"}]})
    body = json.loads(req.content)
    if body.get("stream"):
        nd = '{"message":{"content":"При"}}\n{"message":{"content":"вет"},"done":true}\n'
        return httpx.Response(200, content=nd.encode())
    return httpx.Response(200, json={"message": {"content": "Привет!"}, "done": True})


async def test_ollama_complete_stream_list():
    p = OllamaProvider("http://x", "llama3", transport=httpx.MockTransport(_ollama_handler))
    assert await p.complete([{"role": "user", "content": "hi"}]) == "Привет!"
    assert await p.list_models() == ["llama3"]
    chunks = [c async for c in p.stream([{"role": "user", "content": "hi"}])]
    assert "".join(chunks) == "Привет"


async def test_ollama_http_error_becomes_llmerror():
    def handler(req):
        return httpx.Response(500, text="boom")

    p = OllamaProvider("http://x", "llama3", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError):
        await p.complete([{"role": "user", "content": "hi"}])


# ---- OpenAI + tool calling ----

def _openai_handler(req: httpx.Request) -> httpx.Response:
    assert req.headers.get("Authorization") == "Bearer sk-test"
    body = json.loads(req.content)
    messages = body["messages"]
    if any(m.get("role") == "tool" for m in messages):
        return httpx.Response(200, json={"choices": [{"message": {"content": "Готово: 22"}}]})
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "calculate",
                                    "arguments": '{"expression": "2 + 2 * 10"}',
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )


async def test_openai_tool_calling_loop():
    p = OpenAIProvider(
        "http://y", "gpt", api_key="sk-test", transport=httpx.MockTransport(_openai_handler)
    )
    result = await run_with_tools(
        p, [{"role": "user", "content": "посчитай"}], default_registry()
    )
    assert result == "Готово: 22"
