"""Chat/Command Center endpoint.

Phase 1: a stateless completion endpoint backed by the AI Orchestrator. It
holds a conversation but does not yet emit or execute PlannedActions — see
services/agent/orchestrator.py for why that boundary is deliberate.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.agent.orchestrator import Orchestrator
from services.agent.providers.base import AIProviderError, Message
from services.agent.providers.factory import get_provider

from app.core.config import get_settings
from app.core.errors import CyberAIError

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    model: str
    provider: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    try:
        provider = get_provider(
            settings.ai_provider, settings.gemini_api_key, settings.gemini_model
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    orchestrator = Orchestrator(provider)
    conversation = [Message(role=m.role, content=m.content) for m in request.messages]

    try:
        result = await orchestrator.reply(conversation)
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except CyberAIError:
        raise

    return ChatResponse(reply=result.text, model=result.model, provider=result.provider)
