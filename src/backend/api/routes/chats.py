from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.chat import Chat
from backend.models.user import User
from backend.repositories.chat_repository import ChatRepository
from backend.schemas.chat import ChatCreate, ChatRead, ChatRename

router = APIRouter(prefix="/chats", tags=["Чаты"])


async def get_owned_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Chat:
    """Достать чат по id для текущего пользователя. Если чат не найден, бросить 404."""
    chat = await ChatRepository(session).get(chat_id, current_user.id)

    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден",
        )
    
    return chat


@router.get("", response_model=list[ChatRead])
async def list_chats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Chat]:
    """Список чатов текущего пользователя"""
    return await ChatRepository(session).list_by_user(current_user.id)


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(
    data: ChatCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Chat:
    """Создать новый чат"""
    return await ChatRepository(session).create(current_user.id, data.title)


@router.patch("/{chat_id}", response_model=ChatRead)
async def rename_chat(
    data: ChatRename,
    chat: Chat = Depends(get_owned_chat),
    session: AsyncSession = Depends(get_session),
) -> Chat:
    """Переименовать чат"""
    return await ChatRepository(session).rename(chat, data.title)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat: Chat = Depends(get_owned_chat),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Удалить чат"""
    await ChatRepository(session).delete(chat)
