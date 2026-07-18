from fastapi import APIRouter

from backend.api.routes.auth import router as auth_router
from backend.api.routes.chats import router as chats_router
from backend.api.routes.messages import router as messages_router
from backend.api.routes.models import router as models_router
from backend.api.routes.tools import router as tools_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chats_router)
api_router.include_router(messages_router)
api_router.include_router(models_router)
api_router.include_router(tools_router)
