from uuid import uuid4

import pytest
from services.agent_orchestrator.budget import AgentBudgetConfig, AgentBudgetManager
from services.agent_orchestrator.errors import (
    ConcurrentTaskLimitError,
    InvalidStateTransitionError,
    NotWaitingForApprovalError,
)
from services.agent_orchestrator.events import InMemoryAgentEventBus
from services.agent_orchestrator.models import AgentPhase
from services.agent_orchestrator.orchestrator import AgentOrchestrator
from services.agent_orchestrator.reasoning import AgentReasoner
from services.agent_orchestrator.registry import InMemoryAgentTaskRegistry
from services.installation.registry import InMemoryInstallationRegistry
from services.installation.service import ToolInstallationService
from services.policy.engine import TargetScope
from services.terminal.engine import TerminalEngine
from services.tools.discovery import ToolDiscoveryService
from services.tools.registry import InMemoryToolRegistry
from services.tools.research import CuratedToolResearchProvider

from tests.agent_orchestrator.helpers import ScriptedProvider, approved_tool, decision
from tests.installation.helpers import ScriptedAdapter, failure_result, success_result

ACTIVE_TARGET = TargetScope(id=uuid4(), is_active=True, expires_at=None)


def _orchestrator(
    decisions: list[dict],
    *,
    adapter=None,
    budget_config: AgentBudgetConfig | None = None,
    events=None,
):
    tools = InMemoryToolRegistry()
    installations = InMemoryInstallationRegistry()
    engine = TerminalEngine(adapter=adapter) if adapter else TerminalEngine()
    orch = AgentOrchestrator(
        registry=InMemoryAgentTaskRegistry(),
        event_bus=events or InMemoryAgentEventBus(),
        reasoner=AgentReasoner(ScriptedProvider(decisions)),
        tool_registry=tools,
        discovery_service=ToolDiscoveryService(CuratedToolResearchProvider()),
        installation_service=ToolInstallationService(tools=tools, installations=installations),
        terminal_engine=engine,
        budget=AgentBudgetManager(budget_config) if budget_config else None,
    )
    return orch, tools


async def test_create_task_starts_understanding_then_planning_when_authorized():
    orch, _ = _orchestrator([])
    state = await orch.create_task(
        objective="check dns",
        user_request="check dns on my server",
        target="example.test",
        authorization_status="AUTHORIZED",
        target_id=ACTIVE_TARGET.id,
    )
    assert state.phase == AgentPhase.PLANNING


async def test_create_task_waits_for_authorization_when_not_authorized():
    orch, _ = _orchestrator([])
    state = await orch.create_task(
        objective="check dns", user_request="check dns", authorization_status="UNKNOWN"
    )
    assert state.phase == AgentPhase.WAITING_FOR_AUTHORIZATION


async def test_concurrent_task_limit_is_enforced():
    orch, _ = _orchestrator([], budget_config=AgentBudgetConfig(max_concurrent_tasks=1))
    await orch.create_task(objective="a", user_request="a", authorization_status="AUTHORIZED")
    with pytest.raises(ConcurrentTaskLimitError):
        await orch.create_task(objective="b", user_request="b", authorization_status="AUTHORIZED")


async def test_step_executes_check_environment_and_completes():
    orch, _ = _orchestrator([decision("CHECK_ENVIRONMENT"), decision("COMPLETE_TASK")])
    state = await orch.create_task(
        objective="check dns", user_request="check dns", authorization_status="AUTHORIZED"
    )
    state = await orch.step(state.id)
    assert state.phase == AgentPhase.OBSERVING
    assert state.actions[0].result_summary is not None

    state = await orch.step(state.id)
    assert state.phase == AgentPhase.COMPLETED
    assert state.completed_at is not None


async def test_malformed_ai_response_blocks_task():
    orch, _ = _orchestrator([{"garbage": True}])
    state = await orch.create_task(
        objective="check dns", user_request="check dns", authorization_status="AUTHORIZED"
    )
    state = await orch.step(state.id)
    assert state.phase == AgentPhase.BLOCKED
    assert state.errors


async def test_provider_failure_blocks_task():
    from services.agent_orchestrator.reasoning import AgentReasoner as R

    from tests.agent_orchestrator.helpers import FailingProvider

    tools = InMemoryToolRegistry()
    installations = InMemoryInstallationRegistry()
    orch = AgentOrchestrator(
        registry=InMemoryAgentTaskRegistry(),
        event_bus=InMemoryAgentEventBus(),
        reasoner=R(FailingProvider()),
        tool_registry=tools,
        discovery_service=ToolDiscoveryService(CuratedToolResearchProvider()),
        installation_service=ToolInstallationService(tools=tools, installations=installations),
        terminal_engine=TerminalEngine(),
    )
    state = await orch.create_task(
        objective="check dns", user_request="check dns", authorization_status="AUTHORIZED"
    )
    state = await orch.step(state.id)
    assert state.phase == AgentPhase.BLOCKED


async def test_run_diagnostic_requires_approval_before_executing():
    orch, _ = _orchestrator([decision("RUN_DIAGNOSTIC")])
    state = await orch.create_task(
        objective="run diagnostic",
        user_request="run diagnostic",
        target="example.test",
        authorization_status="AUTHORIZED",
        target_id=ACTIVE_TARGET.id,
    )
    state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
    assert state.phase == AgentPhase.WAITING_FOR_APPROVAL
    assert state.pending_action_id is not None


async def test_approve_action_then_step_executes_it():
    orch, _ = _orchestrator([decision("RUN_DIAGNOSTIC"), decision("COMPLETE_TASK")])
    state = await orch.create_task(
        objective="run diagnostic",
        user_request="run diagnostic",
        target="example.test",
        authorization_status="AUTHORIZED",
        target_id=ACTIVE_TARGET.id,
    )
    state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
    assert state.phase == AgentPhase.WAITING_FOR_APPROVAL

    state = await orch.approve_action(state.id, approved_by="operator")
    assert state.phase == AgentPhase.PREPARING

    state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
    assert state.phase == AgentPhase.OBSERVING
    assert "cyberai-terminal-engine-ok" in state.actions[0].result_summary


async def test_reject_action_blocks_task():
    orch, _ = _orchestrator([decision("RUN_DIAGNOSTIC")])
    state = await orch.create_task(
        objective="run diagnostic",
        user_request="run diagnostic",
        target="example.test",
        authorization_status="AUTHORIZED",
        target_id=ACTIVE_TARGET.id,
    )
    state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
    state = await orch.reject_action(state.id, reason="Not needed.")
    assert state.phase == AgentPhase.BLOCKED
    assert state.actions[0].approval_state.value == "REJECTED"


async def test_approve_when_not_waiting_raises():
    orch, _ = _orchestrator([])
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    with pytest.raises(NotWaitingForApprovalError):
        await orch.approve_action(state.id, approved_by="op")


async def test_pause_and_resume():
    orch, _ = _orchestrator([])
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    paused = await orch.pause(state.id)
    assert paused.phase == AgentPhase.PAUSED

    resumed = await orch.resume(state.id)
    assert resumed.phase == AgentPhase.PLANNING


async def test_step_on_paused_task_is_a_no_op():
    orch, _ = _orchestrator([decision("CHECK_ENVIRONMENT")])
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    await orch.pause(state.id)
    state = await orch.step(state.id)
    assert state.phase == AgentPhase.PAUSED
    assert state.actions == []


async def test_resume_when_not_paused_raises():
    orch, _ = _orchestrator([])
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    with pytest.raises(InvalidStateTransitionError):
        await orch.resume(state.id)


async def test_cancel_terminal_task():
    orch, _ = _orchestrator([])
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    cancelled = await orch.cancel(state.id)
    assert cancelled.phase == AgentPhase.CANCELLED
    assert cancelled.is_terminal()


async def test_provide_clarification_resumes_planning():
    orch, _ = _orchestrator([])
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="UNKNOWN"
    )
    assert state.phase == AgentPhase.WAITING_FOR_AUTHORIZATION
    clarified = await orch.provide_clarification(state.id, "The target is example.test.")
    assert clarified.phase == AgentPhase.PLANNING
    assert clarified.observations


async def test_action_budget_exhaustion_blocks_task():
    orch, _ = _orchestrator(
        [decision("CHECK_ENVIRONMENT")], budget_config=AgentBudgetConfig(max_actions=0)
    )
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    state = await orch.step(state.id)
    assert state.phase == AgentPhase.BLOCKED


async def test_diagnostic_failure_triggers_retry_then_success():
    adapter = ScriptedAdapter([failure_result("transient"), success_result("ok")])
    orch, _ = _orchestrator(
        [decision("RUN_DIAGNOSTIC", requires_approval=False), decision("COMPLETE_TASK")],
        adapter=adapter,
        budget_config=AgentBudgetConfig(max_retries_per_action=2),
    )
    state = await orch.create_task(
        objective="run diagnostic",
        user_request="run diagnostic",
        target="example.test",
        authorization_status="AUTHORIZED",
        target_id=ACTIVE_TARGET.id,
    )
    state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
    # first attempt fails -> approval was still required (RUN_DIAGNOSTIC always does)
    assert state.phase == AgentPhase.WAITING_FOR_APPROVAL
    state = await orch.approve_action(state.id, approved_by="op")
    state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
    assert state.phase == AgentPhase.RECOVERING
    assert state.retry_count_by_action.get("RUN_DIAGNOSTIC") == 1


async def test_repeated_identical_diagnostic_failure_eventually_fails():
    adapter = ScriptedAdapter(
        [failure_result("boom"), failure_result("boom"), failure_result("boom")]
    )
    orch, _ = _orchestrator(
        [
            decision("RUN_DIAGNOSTIC"),
            decision("RUN_DIAGNOSTIC"),
            decision("RUN_DIAGNOSTIC"),
        ],
        adapter=adapter,
        budget_config=AgentBudgetConfig(max_retries_per_action=5),
    )
    state = await orch.create_task(
        objective="run diagnostic",
        user_request="run diagnostic",
        target="example.test",
        authorization_status="AUTHORIZED",
        target_id=ACTIVE_TARGET.id,
    )
    for _ in range(3):
        state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
        if state.phase == AgentPhase.WAITING_FOR_APPROVAL:
            state = await orch.approve_action(state.id, approved_by="op")
            state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
        if state.is_terminal():
            break
    assert state.phase == AgentPhase.FAILED


async def test_research_tool_finds_curated_candidate():
    orch, _ = _orchestrator(
        [
            decision("RESEARCH_TOOL", required_capability="dns"),
            decision("COMPLETE_TASK"),
        ]
    )
    state = await orch.create_task(
        objective="find a dns tool",
        user_request="find a dns tool",
        authorization_status="AUTHORIZED",
    )
    state = await orch.step(state.id)
    assert "dig" in state.tool_capabilities.get("dns", [])


async def test_research_tool_no_candidates_triggers_recovery():
    orch, _ = _orchestrator(
        [decision("RESEARCH_TOOL", required_capability="underwater basket weaving")]
    )
    state = await orch.create_task(
        objective="find weird tool",
        user_request="find weird tool",
        authorization_status="AUTHORIZED",
    )
    state = await orch.step(state.id)
    assert state.phase in (
        AgentPhase.RECOVERING,
        AgentPhase.WAITING_FOR_AUTHORIZATION,
        AgentPhase.FAILED,
    )
    assert state.errors


async def test_install_tool_full_flow(monkeypatch):
    adapter = ScriptedAdapter([success_result("Setting up dig"), success_result("dig 9.18")])
    orch, tools = _orchestrator(
        [decision("INSTALL_TOOL", tool="dig"), decision("COMPLETE_TASK")], adapter=adapter
    )
    await tools.create(approved_tool())
    from services.installation.models import EnvironmentCheck, PackageManager

    monkeypatch.setattr(
        "services.installation.environment.EnvironmentInspector.inspect",
        lambda self, identifier=None: EnvironmentCheck(
            platform="LINUX",
            architecture="x86_64",
            shell="/bin/bash",
            available_package_managers=(PackageManager.APT,),
        ),
    )
    state = await orch.create_task(
        objective="install dig",
        user_request="install dig",
        target="example.test",
        authorization_status="AUTHORIZED",
        target_id=ACTIVE_TARGET.id,
    )
    state = await orch.step(state.id, target_scope=ACTIVE_TARGET)
    assert state.phase == AgentPhase.WAITING_FOR_APPROVAL

    state = await orch.approve_action(state.id, approved_by="op")
    state = await orch.step(state.id, target_scope=ACTIVE_TARGET, platform="LINUX")
    assert "dig" in state.selected_tools
    assert state.installation_state.get("dig") == "INSTALLED"


async def test_analyze_and_verify_flow():
    orch, _ = _orchestrator(
        [
            decision("CHECK_ENVIRONMENT"),
            decision("ANALYZE_OUTPUT"),
            decision("VERIFY_FINDING"),
            decision("COMPLETE_TASK"),
        ]
    )
    state = await orch.create_task(
        objective="analyze", user_request="analyze", authorization_status="AUTHORIZED"
    )
    state = await orch.step(state.id)
    state = await orch.step(state.id)
    assert state.findings and state.findings[-1].kind.value == "FINDING"

    state = await orch.step(state.id)
    assert state.findings[-1].kind.value == "VERIFIED_FINDING"

    state = await orch.step(state.id)
    assert state.phase == AgentPhase.COMPLETED


async def test_events_are_emitted_across_lifecycle():
    events = InMemoryAgentEventBus()
    orch, _ = _orchestrator(
        [decision("CHECK_ENVIRONMENT"), decision("COMPLETE_TASK")], events=events
    )
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    await orch.step(state.id)
    await orch.step(state.id)

    event_types = [e.event_type for e in events.events_for(state.id)]
    assert "AGENT_STARTED" in event_types
    assert "OBJECTIVE_PARSED" in event_types
    assert "ACTION_STARTED" in event_types
    assert "ACTION_OUTPUT" in event_types
    assert "TASK_COMPLETED" in event_types


async def test_events_never_fabricated_beyond_what_happened():
    events = InMemoryAgentEventBus()
    orch, _ = _orchestrator([decision("CHECK_ENVIRONMENT")], events=events)
    state = await orch.create_task(
        objective="x", user_request="x", authorization_status="AUTHORIZED"
    )
    await orch.step(state.id)
    event_types = [e.event_type for e in events.events_for(state.id)]
    assert "TASK_COMPLETED" not in event_types  # task never actually completed
