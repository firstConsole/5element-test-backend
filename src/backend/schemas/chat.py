from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatCreate(BaseModel):
    title: str = Field(default="Новый чат", min_length=1, max_length=255)


class ChatRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
