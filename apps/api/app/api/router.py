from fastapi import APIRouter

from app.api.routes import agent, ai, chat, health, installation, targets, terminal, termux, tools

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(ai.router)
api_router.include_router(chat.router)
api_router.include_router(targets.router)
api_router.include_router(terminal.router)
api_router.include_router(termux.router)
api_router.include_router(tools.router)
api_router.include_router(installation.router)
api_router.include_router(agent.router)
