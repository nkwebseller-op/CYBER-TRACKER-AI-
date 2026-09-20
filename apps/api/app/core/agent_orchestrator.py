"""Dependency wiring for the autonomous Agent Orchestrator (Phase 12).

Reuses the exact same AI provider factory the chat pipeline uses (Phase
4) — there is no second AI integration — and the exact same
TerminalEngine / ToolRegistry / ToolInstallationService singletons every
prior phase already wired up.
"""

import asyncio
from functools import lru_cache

from fastapi import Depends
from services.agent.providers.factory import get_provider
from services.agent_orchestrator.budget import AgentBudgetManager
from services.agent_orchestrator.events import AgentEvent, AgentEventBus, InMemoryAgentEventBus
from services.agent_orchestrator.orchestrator import AgentOrchestrator
from services.agent_orchestrator.reasoning import AgentReasoner
from services.agent_orchestrator.registry import AgentTaskRegistry
from services.installation.service import ToolInstallationService
from services.tools.registry import ToolRegistry
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.installation import get_installation_service
from app.core.terminal_engine import get_terminal_engine
from app.core.tools import get_discovery_service, get_tool_registry
from app.db.agent_repository import SqlAlchemyAgentTaskRegistry
from app.db.session import get_db


def get_agent_task_registry(db: AsyncSession = Depends(get_db)) -> AgentTaskRegistry:
    return SqlAlchemyAgentTaskRegistry(db)


class _WebSocketForwardingEventBus(InMemoryAgentEventBus):
    """Forwards every published event to the existing WebSocket hub
    (app/ws/gateway.py) in addition to keeping the in-memory history that
    GET /api/agent/tasks/{id}/events reads — the same hub Phase 1 already
    built for live terminal/AI-activity streaming, not a second
    transport."""

    def publish(self, event: AgentEvent) -> None:
        super().publish(event)
        from app.ws.gateway import hub

        message = {
            "type": "agent_event",
            "taskId": str(event.task_id),
            "eventType": event.event_type,
            "data": event.data,
        }
        try:
            asyncio.get_running_loop().create_task(hub.broadcast(message))
        except RuntimeError:
            pass  # no running event loop (e.g. a sync test) — history is still kept


@lru_cache
def get_agent_event_bus() -> AgentEventBus:
    return _WebSocketForwardingEventBus()


@lru_cache
def get_agent_budget_manager() -> AgentBudgetManager:
    return AgentBudgetManager()


def get_agent_reasoner() -> AgentReasoner:
    settings = get_settings()
    provider = get_provider(
        settings.ai_provider,
        settings.gemini_api_key,
        settings.gemini_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_output_tokens=settings.ai_max_output_tokens,
    )
    return AgentReasoner(provider)


def get_agent_orchestrator(
    registry: AgentTaskRegistry = Depends(get_agent_task_registry),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    installation_service: ToolInstallationService = Depends(get_installation_service),
) -> AgentOrchestrator:
    return AgentOrchestrator(
        registry=registry,
        event_bus=get_agent_event_bus(),
        reasoner=get_agent_reasoner(),
        tool_registry=tool_registry,
        discovery_service=get_discovery_service(),
        installation_service=installation_service,
        terminal_engine=get_terminal_engine(),
        budget=get_agent_budget_manager(),
    )
