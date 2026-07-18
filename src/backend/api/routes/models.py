from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.model import ModelsResponse
from backend.services.llm import LLMError, LLMProvider, get_llm_provider

router = APIRouter(prefix="/models", tags=["Доступные модели LLM-провайдера"])


@router.get("", response_model=ModelsResponse)
async def list_models(
    _current_user: User = Depends(get_current_user),
    provider: LLMProvider = Depends(get_llm_provider),
) -> ModelsResponse:
    """Список моделей, доступных у текущего провайдера, и модель по умолчанию"""

    try:
        models = await provider.list_models()
        
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка LLM-провайдера: {exc}",
        ) from exc

    return ModelsResponse(
        provider=provider.name,
        default=provider.model,
        models=models,
    )
