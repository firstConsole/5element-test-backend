from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.routes.chats import get_owned_chat
from backend.core.database import get_session
from backend.models.chat import Chat
from backend.models.message import Message, MessageRole
from backend.repositories.message_repository import MessageRepository
from backend.schemas.message import MessageCreate, MessageRead, MessageWithTools
from backend.services.llm import (
    ChatMessage,
    LLMError,
    LLMProvider,
    default_registry,
    get_llm_provider,
    run_with_tools,
)

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["Сообщения"])


def _to_chat_messages(messages: list[Message]) -> list[ChatMessage]:
    """История в формате, понятном LLM-провайдеру."""
    return [{"role": m.role.value, "content": m.content} for m in messages]


def _sse(payload: dict) -> str:
    """Сформировать одно SSE-событие."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _touch_chat(session: AsyncSession, chat: Chat) -> None:
    """Подвинуть чат наверх списка (обновить updated_at)."""
    chat.updated_at = datetime.now(UTC)
    await session.commit()


@router.get("", response_model=list[MessageRead])
async def list_messages(
    chat: Chat = Depends(get_owned_chat),
    session: AsyncSession = Depends(get_session),
) -> list[Message]:
    """История сообщений чата (по возрастанию времени)."""
    return await MessageRepository(session).list_by_chat(chat.id)


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    chat: Chat = Depends(get_owned_chat),
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> Message:
    """Отправить сообщение и получить ответ модели (без стрима)"""

    repo = MessageRepository(session)

    await repo.add(chat.id, MessageRole.user, data.content)
    
    history = await repo.list_by_chat(chat.id)

    try:
        answer = await provider.complete(_to_chat_messages(history), model=data.model)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка LLM-провайдера: {exc}",
        ) from exc

    assistant = await repo.add(chat.id, MessageRole.assistant, answer)

    await _touch_chat(session, chat)

    return assistant


@router.post(
    "/tools",
    response_model=MessageWithTools,
    status_code=status.HTTP_201_CREATED,
)
async def send_message_with_tools(
    data: MessageCreate,
    chat: Chat = Depends(get_owned_chat),
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> MessageWithTools:
    """Отправить сообщение с включённым tool calling.

    Возвращает ответ ассистента и список инструментов, которые модель
    фактически вызвала в процессе генерации.
    """

    repo = MessageRepository(session)

    await repo.add(chat.id, MessageRole.user, data.content)

    history = await repo.list_by_chat(chat.id)

    try:
        result = await run_with_tools(
            provider,
            _to_chat_messages(history),
            registry=default_registry(),
            model=data.model,
        )

    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка LLM-провайдера: {exc}",
        ) from exc

    assistant = await repo.add(chat.id, MessageRole.assistant, result.content)
    await _touch_chat(session, chat)

    response = MessageWithTools.model_validate(assistant, from_attributes=True)
    response.tools_used = result.tools_used
    return response


@router.post("/stream")
async def send_message_stream(
    data: MessageCreate,
    chat: Chat = Depends(get_owned_chat),
    session: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> StreamingResponse:
    repo = MessageRepository(session)

    await repo.add(chat.id, MessageRole.user, data.content)

    history = await repo.list_by_chat(chat.id)
    payload = _to_chat_messages(history)

    async def event_stream() -> AsyncIterator[str]:
        collected: list[str] = []
        try:
            async for piece in provider.stream(payload, model=data.model):
                collected.append(piece)
                yield _sse({"delta": piece})
        except LLMError as exc:
            yield _sse({"error": f"Ошибка LLM-провайдера: {exc}"})
            return

        assistant = await repo.add(
            chat.id, MessageRole.assistant, "".join(collected)
        )
        await _touch_chat(session, chat)
        yield _sse({"done": True, "message_id": assistant.id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
