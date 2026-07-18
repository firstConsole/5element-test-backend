from fastapi import APIRouter

from backend.api.routes.auth import router as auth_router
from backend.api.routes.chats import router as chats_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chats_router)
