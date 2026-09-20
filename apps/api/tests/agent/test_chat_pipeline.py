import pytest
from services.agent.chat_pipeline import (
    ChatPipeline,
    ChatPipelineError,
    ChatPipelineErrorCode,
    ChatTurnRequest,
)
from services.agent.conversation_context import ConversationContext
from services.agent.providers.base import AIProviderError, AIProviderErrorCode

from tests.fakes import FakeProvider, valid_ai_response_payload


def _turn(message: str, conversation_id: str = "conv-1") -> ChatTurnRequest:
    return ChatTurnRequest(
        request_id="req-1",
        conversation_id=conversation_id,
        message=message,
        context=ConversationContext(conversation_id=conversation_id),
    )


async def test_rejects_empty_message_without_calling_provider():
    provider = FakeProvider(structured_responses=[])
    pipeline = ChatPipeline(provider)

    with pytest.raises(ChatPipelineError) as exc_info:
        await pipeline.handle_message(_turn("   "))

    assert exc_info.value.code == ChatPipelineErrorCode.EMPTY_MESSAGE
    assert provider.calls == []


async def test_rejects_message_over_max_length():
    provider = FakeProvider(structured_responses=[])
    pipeline = ChatPipeline(provider, max_input_chars=10)

    with pytest.raises(ChatPipelineError) as exc_info:
        await pipeline.handle_message(_turn("this message is definitely too long"))

    assert exc_info.value.code == ChatPipelineErrorCode.INVALID_INPUT
    assert provider.calls == []


async def test_successful_turn_returns_validated_response_with_conversation_id_enforced():
    payload = valid_ai_response_payload(conversation_id="untrusted-id")
    provider = FakeProvider(structured_responses=[payload])
    pipeline = ChatPipeline(provider)

    turn = _turn("Analyze my authorized API.", conversation_id="conv-real")
    response = await pipeline.handle_message(turn)

    # The application's own conversation id wins over anything the model echoed.
    assert response.task_plan.conversation_id == "conv-real"
    assert response.task_intent.authorization_status.value == "UNKNOWN"


async def test_malformed_provider_response_raises_invalid_task():
    provider = FakeProvider(structured_responses=[{"message": "incomplete"}])
    pipeline = ChatPipeline(provider)

    with pytest.raises(ChatPipelineError) as exc_info:
        await pipeline.handle_message(_turn("hello"))

    assert exc_info.value.code == ChatPipelineErrorCode.INVALID_TASK


async def test_provider_timeout_is_mapped_to_pipeline_timeout():
    provider = FakeProvider(
        structured_responses=[AIProviderError("timed out", code=AIProviderErrorCode.TIMEOUT)]
    )
    pipeline = ChatPipeline(provider, retry_max_attempts=1)

    with pytest.raises(ChatPipelineError) as exc_info:
        await pipeline.handle_message(_turn("hello"))

    assert exc_info.value.code == ChatPipelineErrorCode.TIMEOUT


async def test_retries_transient_failure_before_succeeding():
    provider = FakeProvider(
        structured_responses=[
            AIProviderError("temporary", code=AIProviderErrorCode.UNAVAILABLE),
            valid_ai_response_payload(),
        ]
    )
    pipeline = ChatPipeline(provider, retry_max_attempts=3, retry_base_delay_seconds=0.001)

    response = await pipeline.handle_message(_turn("hello"))

    assert response.message == "Understood, here is the plan."
    assert len(provider.calls) == 2
