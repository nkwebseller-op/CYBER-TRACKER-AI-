"""Shared test doubles for AIProvider — never call the real Gemini API in
automated tests."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from services.agent.providers.base import (
    AIProvider,
    AIProviderError,
    CompletionResult,
    Message,
    ProviderHealth,
    ProviderHealthStatus,
    StructuredCompletionResult,
)


def valid_ai_response_payload(
    *, conversation_id: str = "conv-test", objective: str = "Test objective"
) -> dict:
    task_intent = {
        "id": "intent-test",
        "objective": objective,
        "target": "unknown",
        "targetType": "unknown",
        "requestedAction": "security_assessment",
        "constraints": [],
        "authorizationStatus": "UNKNOWN",
        "riskLevel": "MEDIUM",
        "requiresApproval": "APPROVAL_REQUIRED",
        "missingInformation": ["target", "authorization"],
    }
    now = datetime.now(UTC).isoformat()
    return {
        "message": "Understood, here is the plan.",
        "taskIntent": task_intent,
        "taskPlan": {
            "id": "plan-test",
            "conversationId": conversation_id,
            "taskIntent": task_intent,
            "workflow": [
                {"key": "UNDERSTAND", "label": "Understand", "status": "active"},
                {"key": "RESEARCH", "label": "Research", "status": "pending"},
                {"key": "SELECT", "label": "Select", "status": "pending"},
                {"key": "APPROVE", "label": "Approve", "status": "pending"},
                {"key": "PREPARE", "label": "Prepare", "status": "pending"},
                {"key": "RUN", "label": "Run", "status": "pending"},
                {"key": "ANALYZE", "label": "Analyze", "status": "pending"},
                {"key": "REPORT", "label": "Report", "status": "pending"},
            ],
            "status": "WAITING_FOR_INFORMATION",
            "createdAt": now,
        },
        "authorizationStatus": "UNKNOWN",
        "riskLevel": "MEDIUM",
        "requiresApproval": "APPROVAL_REQUIRED",
        "missingInformation": ["target", "authorization"],
        "nextAction": "Provide the missing target and authorization evidence.",
    }


class FakeProvider(AIProvider):
    """Configurable stand-in for AIProvider. Queue responses/errors and
    this plays them back in order, recording every call it received."""

    name = "fake"

    def __init__(
        self,
        *,
        structured_responses: list[dict | Exception] | None = None,
        health: ProviderHealth | None = None,
    ) -> None:
        self._structured_responses = list(structured_responses or [])
        self._health = health or ProviderHealth(
            provider=self.name, status=ProviderHealthStatus.CONNECTED
        )
        self.calls: list[list[Message]] = []

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> CompletionResult:
        return CompletionResult(text="fake completion", model="fake-1", provider=self.name)

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        yield "fake"

    async def generate_structured(
        self,
        messages: list[Message],
        *,
        schema: dict,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> StructuredCompletionResult:
        self.calls.append(messages)
        if not self._structured_responses:
            raise AssertionError("FakeProvider ran out of queued responses")

        next_item = self._structured_responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item

        return StructuredCompletionResult(
            data=next_item, raw_text="", model="fake-1", provider=self.name
        )

    async def health_check(self) -> ProviderHealth:
        return self._health


__all__ = ["FakeProvider", "valid_ai_response_payload", "AIProviderError"]
