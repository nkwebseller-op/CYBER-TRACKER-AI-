from fastapi import APIRouter

from app.api.routes import chat, health, targets

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(targets.router)
