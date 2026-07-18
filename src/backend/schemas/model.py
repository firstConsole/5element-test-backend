from pydantic import BaseModel


class ModelsResponse(BaseModel):
    provider: str  # ollama | openai
    default: str  # модель по умолчанию (из конфига)
    models: list[str]  # список доступных моделей
