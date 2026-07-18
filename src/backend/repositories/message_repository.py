from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.message import Message, MessageRole


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_chat(self, chat_id: int) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(result.scalars().all())

    async def add(
        self,
        chat_id: int,
        role: MessageRole,
        content: str,
    ) -> Message:
        message = Message(chat_id=chat_id, role=role, content=content)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message
