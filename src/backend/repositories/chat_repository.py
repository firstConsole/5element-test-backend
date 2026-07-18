from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: int) -> list[Chat]:
        result = await self.session.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, chat_id: int, user_id: int) -> Chat | None:
        """Вернуть чат, только если он принадлежит пользователю."""
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, title: str) -> Chat:
        chat = Chat(user_id=user_id, title=title)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def rename(self, chat: Chat, title: str) -> Chat:
        chat.title = title
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def delete(self, chat: Chat) -> None:
        await self.session.delete(chat)
        await self.session.commit()
