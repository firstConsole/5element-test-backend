from fastapi import APIRouter, Depends

from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.tool import ToolSpec
from backend.services.llm import default_registry

router = APIRouter(prefix="/tools", tags=["Инструменты (tool calling)"])


@router.get("", response_model=list[ToolSpec])
async def list_tools(
    _current_user: User = Depends(get_current_user),
) -> list[ToolSpec]:
    return [
        ToolSpec(name=t.name, description=t.description, parameters=t.parameters)
        for t in default_registry().all()
    ]
