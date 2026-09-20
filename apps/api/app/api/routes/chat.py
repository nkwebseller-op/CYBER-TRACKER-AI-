"""Chat/Command Center endpoints.

- `POST /api/chat` (Phase 1): a stateless free-form completion endpoint
  backed by the AI Orchestrator. Kept for backward compatibility.
- `POST /api/chat/message` (Phase 4): the real backend for the Phase 3
  frontend contract (apps/web/src/types/chat.ts ChatMessageRequest /
  ChatMessageResponse). Runs the full
  validate -> context -> provider.generate_structured -> validate pipeline
  in services/agent/chat_pipeline.py and returns a schema-validated
  TaskIntent/TaskPlan — never raw model output.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.agent.chat_pipeline import (
    ChatPipeline,
    ChatPipelineError,
    ChatPipelineErrorCode,
    ChatTurnRequest,
)
from services.agent.conversation_context import ConversationContext
from services.agent.orchestrator import Orchestrator
from services.agent.providers.base import AIProviderError, Message
from services.agent.providers.factory import get_provider

from app.core.config import get_settings
from app.core.errors import CyberAIError
from app.schemas.chat import ChatMessageOut, ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])

_PIPELINE_ERROR_STATUS: dict[ChatPipelineErrorCode, int] = {
    ChatPipelineErrorCode.EMPTY_MESSAGE: 422,
    ChatPipelineErrorCode.INVALID_INPUT: 422,
    ChatPipelineErrorCode.REQUEST_FAILED: 502,
    ChatPipelineErrorCode.TIMEOUT: 504,
    ChatPipelineErrorCode.INVALID_TASK: 422,
    ChatPipelineErrorCode.UNEXPECTED_RESPONSE: 502,
}


def _get_configured_provider():
    settings = get_settings()
    return get_provider(
        settings.ai_provider,
        settings.gemini_api_key,
        settings.gemini_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_output_tokens=settings.ai_max_output_tokens,
    )


# --- Phase 1 endpoint (kept for backward compatibility) ---


class LegacyChatMessage(BaseModel):
    role: str
    content: str


class LegacyChatRequest(BaseModel):
    messages: list[LegacyChatMessage]


class LegacyChatResponse(BaseModel):
    reply: str
    model: str
    provider: str


@router.post("", response_model=LegacyChatResponse)
async def chat(request: LegacyChatRequest) -> LegacyChatResponse:
    try:
        provider = _get_configured_provider()
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

    return LegacyChatResponse(reply=result.text, model=result.model, provider=result.provider)


# --- Phase 4: the real Chat / Command Center backend ---


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    settings = get_settings()

    try:
        provider = _get_configured_provider()
    except AIProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "configuration_error", "message": "The AI provider is not configured."},
        ) from exc

    pipeline = ChatPipeline(
        provider,
        max_input_chars=settings.ai_max_input_chars,
        max_output_tokens=settings.ai_max_output_tokens,
        retry_max_attempts=settings.ai_retry_max_attempts,
        retry_base_delay_seconds=settings.ai_retry_base_delay_seconds,
    )

    # No cross-request conversation history is persisted yet (Phase 3's
    # frontend contract sends only the latest message) — the context is
    # built fresh per turn. Wiring durable history through UserSession /
    # AuditLogEntry is a later phase, not a Phase 4 change.
    context = ConversationContext(conversation_id=request.conversation_id)
    turn = ChatTurnRequest(
        request_id=str(uuid.uuid4()),
        conversation_id=request.conversation_id,
        message=request.message,
        context=context,
    )

    try:
        ai_response = await pipeline.handle_message(turn)
    except ChatPipelineError as exc:
        status_code = _PIPELINE_ERROR_STATUS.get(exc.code, 500)
        raise HTTPException(
            status_code=status_code, detail={"code": exc.code, "message": str(exc)}
        ) from exc

    assistant_message = ChatMessageOut(
        id=f"msg-{uuid.uuid4()}",
        role="assistant",
        content=ai_response.message,
        timestamp=datetime.now(UTC).isoformat(),
        status="completed",
    )

    return ChatMessageResponse(
        message=assistant_message,
        task_intent=ai_response.task_intent,
        task_plan=ai_response.task_plan,
        status="ok",
    )
