from fastapi import APIRouter

from app.api.routes import ai, chat, health, targets, terminal

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(ai.router)
api_router.include_router(chat.router)
api_router.include_router(targets.router)
api_router.include_router(terminal.router)
