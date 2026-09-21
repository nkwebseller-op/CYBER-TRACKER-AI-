"""Chat pipeline: the only path from a validated user message to a
validated AIResponse.

    validate request
      -> build bounded conversation context
      -> build controlled AI request (system instruction + application
         context + user message, each clearly delimited — see prompts.py)
      -> call provider.generate_structured (bounded retries for transient
         errors only)
      -> validate the provider's structured output against AIResponse
      -> return

Nothing here reaches a terminal, a tool, or services/policy directly —
this phase produces planning data only (see module docstring in
services/agent/schemas.py).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

import structlog

from services.agent.conversation_context import (
    ConversationContext,
    bounded_history,
    build_context_summary,
    to_provider_messages,
)
from services.agent.prompts import (
    SYSTEM_INSTRUCTION,
    build_application_context_block,
    build_user_message_block,
)
from services.agent.providers.base import AIProvider, AIProviderError, AIProviderErrorCode, Message
from services.agent.retry import call_with_retry
from services.agent.schemas import (
    GEMINI_RESPONSE_SCHEMA,
    AIResponse,
    AIResponseValidationError,
    parse_ai_response,
)

logger = structlog.get_logger(__name__)


class ChatPipelineErrorCode(StrEnum):
    EMPTY_MESSAGE = "empty_message"
    INVALID_INPUT = "invalid_input"
    REQUEST_FAILED = "request_failed"
    TIMEOUT = "timeout"
    INVALID_TASK = "invalid_task"
    UNEXPECTED_RESPONSE = "unexpected_response"


_PROVIDER_ERROR_TO_PIPELINE_ERROR: dict[AIProviderErrorCode, ChatPipelineErrorCode] = {
    AIProviderErrorCode.MISSING_API_KEY: ChatPipelineErrorCode.REQUEST_FAILED,
    AIProviderErrorCode.INVALID_API_KEY: ChatPipelineErrorCode.REQUEST_FAILED,
    AIProviderErrorCode.CONFIGURATION_ERROR: ChatPipelineErrorCode.REQUEST_FAILED,
    AIProviderErrorCode.UNAVAILABLE: ChatPipelineErrorCode.REQUEST_FAILED,
    AIProviderErrorCode.TIMEOUT: ChatPipelineErrorCode.TIMEOUT,
    AIProviderErrorCode.RATE_LIMITED: ChatPipelineErrorCode.REQUEST_FAILED,
    AIProviderErrorCode.NETWORK_ERROR: ChatPipelineErrorCode.REQUEST_FAILED,
    AIProviderErrorCode.INVALID_RESPONSE: ChatPipelineErrorCode.UNEXPECTED_RESPONSE,
    AIProviderErrorCode.UNKNOWN: ChatPipelineErrorCode.UNEXPECTED_RESPONSE,
}


class ChatPipelineError(RuntimeError):
    def __init__(self, code: ChatPipelineErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class ChatTurnRequest:
    request_id: str
    conversation_id: str
    message: str
    context: ConversationContext


class ChatPipeline:
    def __init__(
        self,
        provider: AIProvider,
        *,
        max_input_chars: int = 4000,
        max_output_tokens: int = 2048,
        retry_max_attempts: int = 3,
        retry_base_delay_seconds: float = 0.5,
    ) -> None:
        self._provider = provider
        self._max_input_chars = max_input_chars
        self._max_output_tokens = max_output_tokens
        self._retry_max_attempts = retry_max_attempts
        self._retry_base_delay_seconds = retry_base_delay_seconds

    async def handle_message(self, turn: ChatTurnRequest) -> AIResponse:
        trimmed = turn.message.strip()

        if not trimmed:
            raise ChatPipelineError(ChatPipelineErrorCode.EMPTY_MESSAGE, "Message cannot be empty.")
        if len(trimmed) > self._max_input_chars:
            raise ChatPipelineError(
                ChatPipelineErrorCode.INVALID_INPUT,
                f"Message is too long (limit is {self._max_input_chars} characters).",
            )

        logger.info(
            "chat_request_received",
            request_id=turn.request_id,
            conversation_id=turn.conversation_id,
            provider=self._provider.name,
            message_length=len(trimmed),
        )

        history = bounded_history(turn.context)
        context_summary = build_context_summary(turn.context)
        provider_messages: list[Message] = [
            Message(role="system", content=SYSTEM_INSTRUCTION),
            Message(
                role="system",
                content=build_application_context_block(context_summary=context_summary),
            ),
            *to_provider_messages(history),
            Message(role="user", content=build_user_message_block(trimmed)),
        ]

        started_at = datetime.now(UTC)

        async def call():
            return await self._provider.generate_structured(
                provider_messages,
                schema=GEMINI_RESPONSE_SCHEMA,
                temperature=0.2,
                max_output_tokens=self._max_output_tokens,
            )

        try:
            result = await call_with_retry(
                call,
                max_attempts=self._retry_max_attempts,
                base_delay_seconds=self._retry_base_delay_seconds,
                operation="chat.generate_structured",
            )
        except AIProviderError as exc:
            latency_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000
            logger.error(
                "chat_request_failed",
                request_id=turn.request_id,
                conversation_id=turn.conversation_id,
                provider=self._provider.name,
                error_code=exc.code,
                latency_ms=latency_ms,
            )
            pipeline_code = _PROVIDER_ERROR_TO_PIPELINE_ERROR.get(
                exc.code, ChatPipelineErrorCode.REQUEST_FAILED
            )
            raise ChatPipelineError(pipeline_code, str(exc)) from exc

        latency_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000

        try:
            ai_response = parse_ai_response(result.data)
        except AIResponseValidationError as exc:
            logger.error(
                "chat_response_validation_failed",
                request_id=turn.request_id,
                conversation_id=turn.conversation_id,
                provider=self._provider.name,
                latency_ms=latency_ms,
                validation_error=str(exc)[:500],
                data_keys=list(result.data.keys()) if isinstance(result.data, dict) else None,
            )
            raise ChatPipelineError(
                ChatPipelineErrorCode.INVALID_TASK,
                "Cyber AI could not produce a valid task plan for that message. "
                "Please try rephrasing it.",
            ) from exc

        # Never trust a provider-echoed conversation id — the application
        # owns that identifier, not the model.
        corrected_plan = ai_response.task_plan.model_copy(
            update={"conversation_id": turn.conversation_id}
        )
        ai_response = ai_response.model_copy(update={"task_plan": corrected_plan})

        logger.info(
            "chat_request_completed",
            request_id=turn.request_id,
            conversation_id=turn.conversation_id,
            provider=self._provider.name,
            model=result.model,
            latency_ms=latency_ms,
            risk_level=ai_response.risk_level,
            requires_approval=ai_response.requires_approval,
        )

        return ai_response
