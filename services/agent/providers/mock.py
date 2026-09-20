"""Deterministic local provider for development/testing.

Never selected unless AI_PROVIDER=mock is explicitly configured — see
services/agent/providers/factory.py and app/core/config.py, which refuses
to let AI_PROVIDER=mock be used when environment=="production". This keeps
the mock provider from accidentally becoming the production provider.
"""

import re
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from services.agent.providers.base import (
    AIProvider,
    CompletionResult,
    Message,
    ProviderHealth,
    ProviderHealthStatus,
    StructuredCompletionResult,
)

_HOST_PATTERN = re.compile(
    r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b|\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b", re.IGNORECASE
)

_TARGET_TYPE_KEYWORDS = [
    ("web_application", ["website", "web app", "web application", "webapp"]),
    ("api", ["api", "endpoint", "rest service", "graphql"]),
    ("cloud_resource", ["cloud", "aws", "azure", "gcp", "s3 bucket", "vpc"]),
    ("mobile_device", ["android", "ios", "mobile device", "mobile app", "phone", "handset"]),
    ("wireless_device", ["bluetooth", "wireless", "wifi", "wi-fi", "ble", "beacon"]),
    ("network_asset", ["network", "lan", "subnet", "vlan", "office network"]),
    ("server", ["server", "vm", "virtual machine", "host", "database server"]),
]

_ENVIRONMENT_KEYWORDS = ["production", "staging", "internal", "development", "dev environment"]


_FENCED_BLOCK_PATTERN = re.compile(r"```\n(.*)\n```", re.DOTALL)


def _find_last_user_message(messages: list[Message]) -> str:
    """Returns the user's raw objective text.

    The pipeline wraps the actual message in a labeled, fenced block (see
    services/agent/prompts.py build_user_message_block) so a real LLM
    provider never mistakes it for an instruction. MockProvider isn't an
    LLM — it just needs the raw text back out of that wrapper.
    """
    for message in reversed(messages):
        if message.role == "user":
            match = _FENCED_BLOCK_PATTERN.search(message.content)
            return match.group(1) if match else message.content
    return ""


class MockProvider(AIProvider):
    """Same deterministic keyword-matching approach as
    apps/web/src/lib/chat/intent-extractor.ts's MockIntentExtractor, kept
    server-side so `AI_PROVIDER=mock` exercises the exact same chat
    pipeline (validation, logging, error handling) as the real Gemini
    provider without any network call."""

    name = "mock"

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> CompletionResult:
        objective = _find_last_user_message(messages)
        return CompletionResult(
            text=f"[mock provider] Received: {objective or '(empty message)'}",
            model="mock-1",
            provider=self.name,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        result = await self.complete(messages, temperature=temperature)
        yield result.text

    async def generate_structured(
        self,
        messages: list[Message],
        *,
        schema: dict,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> StructuredCompletionResult:
        objective = _find_last_user_message(messages).strip()
        normalized = objective.lower()

        target_type = "unknown"
        for candidate_type, keywords in _TARGET_TYPE_KEYWORDS:
            if any(keyword in normalized for keyword in keywords):
                target_type = candidate_type
                break

        host_match = _HOST_PATTERN.search(objective)
        target = host_match.group(0) if host_match else "unknown"

        has_environment = any(keyword in normalized for keyword in _ENVIRONMENT_KEYWORDS)

        missing_information = []
        if target == "unknown":
            missing_information.append("target")
        missing_information.append("authorization")
        if not has_environment:
            missing_information.append("environment")

        now = datetime.now(UTC).isoformat()
        task_intent_id = f"intent-{uuid.uuid4()}"
        task_plan_id = f"plan-{uuid.uuid4()}"

        has_missing_info = len(missing_information) > 0
        understand_status = "active" if has_missing_info else "complete"
        research_status = "pending" if has_missing_info else "active"
        workflow = [
            {"key": "UNDERSTAND", "label": "Understand", "status": understand_status},
            {"key": "RESEARCH", "label": "Research", "status": research_status},
            {"key": "SELECT", "label": "Select", "status": "pending"},
            {"key": "APPROVE", "label": "Approve", "status": "pending"},
            {"key": "PREPARE", "label": "Prepare", "status": "pending"},
            {"key": "RUN", "label": "Run", "status": "pending"},
            {"key": "ANALYZE", "label": "Analyze", "status": "pending"},
            {"key": "REPORT", "label": "Report", "status": "pending"},
        ]

        task_intent = {
            "id": task_intent_id,
            "objective": objective or "unknown",
            "target": target,
            "targetType": target_type,
            "requestedAction": "security_assessment" if objective else "unknown",
            "constraints": [],
            "authorizationStatus": "UNKNOWN",
            "riskLevel": "LOW" if not objective else "MEDIUM",
            "requiresApproval": "APPROVAL_REQUIRED",
            "missingInformation": missing_information,
        }

        plan_status = "WAITING_FOR_INFORMATION" if has_missing_info else "AWAITING_AUTHORIZATION"
        next_action = "Provide the missing information above so Cyber AI can continue planning."

        data = {
            "message": (
                "This is a mock provider response for development/testing. "
                f"Captured objective: {objective or 'none provided'}."
            ),
            "taskIntent": task_intent,
            "taskPlan": {
                "id": task_plan_id,
                "conversationId": "mock-conversation",
                "taskIntent": task_intent,
                "workflow": workflow,
                "status": plan_status,
                "createdAt": now,
            },
            "authorizationStatus": "UNKNOWN",
            "riskLevel": task_intent["riskLevel"],
            "requiresApproval": "APPROVAL_REQUIRED",
            "missingInformation": missing_information,
            "nextAction": next_action,
        }

        return StructuredCompletionResult(
            data=data, raw_text="", model="mock-1", provider=self.name
        )

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name, status=ProviderHealthStatus.CONNECTED, model="mock-1"
        )
