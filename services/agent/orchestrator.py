"""AI Orchestrator: turns a natural-language objective into chat responses
and, later, structured PlannedAction proposals.

Phase 1 scope: the orchestrator can hold a conversation via the configured
AIProvider. It deliberately does NOT yet parse model output into
PlannedAction objects or call the Policy Engine — that's the Task Planner's
job in the next phase, once there's a real action-type registry (see
services/tools) to validate against. Wiring the AI directly to execution
without that registry would be exactly the "blind command execution" this
architecture forbids.
"""

from dataclasses import dataclass

from services.agent.providers.base import AIProvider, Message

SYSTEM_PROMPT = (
    "You are the planning assistant for Cyber AI System, an authorized "
    "cybersecurity assessment platform. You help the user clarify their "
    "authorized security objective and scope. You never suggest or imply "
    "action against a target that has not been explicitly declared as "
    "authorized. You do not output shell commands; you describe objectives "
    "and let the platform's own planner and policy engine decide what, if "
    "anything, may be executed."
)


@dataclass
class OrchestratorReply:
    text: str
    model: str
    provider: str


class Orchestrator:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def reply(self, conversation: list[Message]) -> OrchestratorReply:
        messages = [Message(role="system", content=SYSTEM_PROMPT), *conversation]
        result = await self._provider.complete(messages)
        return OrchestratorReply(text=result.text, model=result.model, provider=result.provider)
