from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import get_session
from backend.main import app
from backend.models import Base
from backend.services.llm.base import ChatResult, LLMProvider, ToolCall
from backend.services.llm.factory import get_llm_provider


class FakeProvider(LLMProvider):
    """Подставной LLM-провайдер для тестов (без сети)."""

    name = "fake"

    def __init__(self) -> None:
        self.model = "fake-model"

    async def complete(self, messages, model=None):
        return "Ответ: " + messages[-1]["content"]

    async def stream(self, messages, model=None):
        for part in ["часть1", "часть2"]:
            yield part

    async def list_models(self):
        return ["fake-model", "other-model"]

    async def chat(self, messages, model=None, tools=None) -> ChatResult:
        # Первый вызов -> просим инструмент; после результата -> финальный ответ.
        if any(m.get("role") == "tool" for m in messages):
            tool_output = [m["content"] for m in messages if m.get("role") == "tool"][-1]
            return ChatResult(content=f"Итог: {tool_output}", tool_calls=[])
        return ChatResult(
            content="",
            tool_calls=[
                ToolCall(id="1", name="calculate", arguments={"expression": "2 + 2 * 10"})
            ],
        )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP-клиент к приложению с in-memory БД и fake-провайдером."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_headers(client: httpx.AsyncClient):
    """Фабрика: регистрирует и логинит пользователя, возвращает заголовок Bearer."""

    async def _make(email: str = "user@example.com") -> dict[str, str]:
        await client.post("/auth/register", json={"email": email, "password": "password1"})
        resp = await client.post(
            "/auth/login", json={"email": email, "password": "password1"}
        )
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _make
