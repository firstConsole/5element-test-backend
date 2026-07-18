from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.message import MessageRole


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    model: str | None = None


class MessageRead(BaseModel):
    """Представление сообщения."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    content: str
    created_at: datetime
