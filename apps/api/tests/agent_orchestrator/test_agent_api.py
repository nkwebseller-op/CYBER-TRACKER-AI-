from uuid import uuid4

from services.agent_orchestrator.events import InMemoryAgentEventBus
from services.agent_orchestrator.orchestrator import AgentOrchestrator
from services.agent_orchestrator.reasoning import AgentReasoner
from services.agent_orchestrator.registry import InMemoryAgentTaskRegistry
from services.installation.registry import InMemoryInstallationRegistry
from services.installation.service import ToolInstallationService
from services.terminal.engine import TerminalEngine
from services.tools.discovery import ToolDiscoveryService
from services.tools.registry import InMemoryToolRegistry
from services.tools.research import CuratedToolResearchProvider

from app.api.routes import agent as agent_routes
from app.core.agent_orchestrator import get_agent_event_bus, get_agent_orchestrator
from app.db.session import get_db
from app.main import app
from tests.agent_orchestrator.helpers import ScriptedProvider, decision


class _FakeTarget:
    def __init__(self, target_id, *, is_active=True):
        self.id = target_id
        self.is_active = is_active
        self.expires_at = None


class _FakeDBSession:
    def __init__(self, target=None):
        self._target = target

    async def get(self, _model, target_id):
        if self._target is not None and self._target.id == target_id:
            return self._target
        return None


def _wire(decisions, *, target_active=True):
    tools = InMemoryToolRegistry()
    installations = InMemoryInstallationRegistry()
    events = InMemoryAgentEventBus()
    orchestrator = AgentOrchestrator(
        registry=InMemoryAgentTaskRegistry(),
        event_bus=events,
        reasoner=AgentReasoner(ScriptedProvider(decisions)),
        tool_registry=tools,
        discovery_service=ToolDiscoveryService(CuratedToolResearchProvider()),
        installation_service=ToolInstallationService(tools=tools, installations=installations),
        terminal_engine=TerminalEngine(),
    )
    target_id = uuid4()
    target = _FakeTarget(target_id, is_active=target_active)

    async def fake_get_db():
        yield _FakeDBSession(target)

    app.dependency_overrides[get_agent_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_agent_event_bus] = lambda: events
    app.dependency_overrides[get_db] = fake_get_db
    return target_id


def _teardown():
    for dep in (get_agent_orchestrator, get_agent_event_bus, get_db):
        app.dependency_overrides.pop(dep, None)


async def test_create_task_endpoint(client):
    _wire([])
    response = await client.post(
        "/api/agent/tasks",
        json={
            "objective": "check dns",
            "userRequest": "check dns",
            "authorizationStatus": "AUTHORIZED",
        },
    )
    assert response.status_code == 201
    assert response.json()["phase"] == "PLANNING"
    _teardown()


async def test_create_task_with_target_resolves_authorization(client):
    target_id = _wire([])
    response = await client.post(
        "/api/agent/tasks",
        json={
            "objective": "check dns",
            "userRequest": "check dns",
            "target": "example.test",
            "targetId": str(target_id),
        },
    )
    assert response.status_code == 201
    assert response.json()["authorizationStatus"] == "AUTHORIZED"
    assert response.json()["phase"] == "PLANNING"
    _teardown()


async def test_create_task_with_inactive_target_waits_for_authorization(client):
    target_id = _wire([], target_active=False)
    response = await client.post(
        "/api/agent/tasks",
        json={
            "objective": "check dns",
            "userRequest": "check dns",
            "target": "example.test",
            "targetId": str(target_id),
        },
    )
    assert response.status_code == 201
    assert response.json()["authorizationStatus"] == "NOT_AUTHORIZED"
    assert response.json()["phase"] == "WAITING_FOR_AUTHORIZATION"
    _teardown()


async def test_get_unknown_task_returns_404(client):
    _wire([])
    response = await client.get(f"/api/agent/tasks/{uuid4()}")
    assert response.status_code == 404
    _teardown()


async def test_step_endpoint_advances_task(client):
    _wire([decision("CHECK_ENVIRONMENT"), decision("COMPLETE_TASK")])
    created = await client.post(
        "/api/agent/tasks",
        json={"objective": "x", "userRequest": "x", "authorizationStatus": "AUTHORIZED"},
    )
    task_id = created.json()["id"]

    step1 = await client.post(f"/api/agent/tasks/{task_id}/step", json={})
    assert step1.status_code == 200
    assert len(step1.json()["actions"]) == 1

    step2 = await client.post(f"/api/agent/tasks/{task_id}/step", json={})
    assert step2.json()["phase"] == "COMPLETED"
    _teardown()


async def test_approval_flow_via_api(client):
    target_id = _wire([decision("RUN_DIAGNOSTIC"), decision("COMPLETE_TASK")])
    created = await client.post(
        "/api/agent/tasks",
        json={
            "objective": "run diagnostic",
            "userRequest": "run diagnostic",
            "target": "example.test",
            "targetId": str(target_id),
        },
    )
    task_id = created.json()["id"]

    step = await client.post(
        f"/api/agent/tasks/{task_id}/step", json={"targetId": str(target_id)}
    )
    assert step.json()["phase"] == "WAITING_FOR_APPROVAL"

    approve = await client.post(
        f"/api/agent/tasks/{task_id}/approve", json={"approvedBy": "operator"}
    )
    assert approve.json()["phase"] == "PREPARING"

    finished = await client.post(
        f"/api/agent/tasks/{task_id}/step", json={"targetId": str(target_id)}
    )
    assert finished.json()["phase"] == "OBSERVING"
    _teardown()


async def test_reject_flow_via_api(client):
    target_id = _wire([decision("RUN_DIAGNOSTIC")])
    created = await client.post(
        "/api/agent/tasks",
        json={
            "objective": "run diagnostic",
            "userRequest": "run diagnostic",
            "target": "example.test",
            "targetId": str(target_id),
        },
    )
    task_id = created.json()["id"]
    await client.post(f"/api/agent/tasks/{task_id}/step", json={"targetId": str(target_id)})

    rejected = await client.post(
        f"/api/agent/tasks/{task_id}/reject", json={"reason": "not now"}
    )
    assert rejected.json()["phase"] == "BLOCKED"
    _teardown()


async def test_pause_resume_cancel_via_api(client):
    _wire([])
    created = await client.post(
        "/api/agent/tasks",
        json={"objective": "x", "userRequest": "x", "authorizationStatus": "AUTHORIZED"},
    )
    task_id = created.json()["id"]

    paused = await client.post(f"/api/agent/tasks/{task_id}/pause")
    assert paused.json()["phase"] == "PAUSED"

    resumed = await client.post(f"/api/agent/tasks/{task_id}/resume")
    assert resumed.json()["phase"] == "PLANNING"

    cancelled = await client.post(f"/api/agent/tasks/{task_id}/cancel")
    assert cancelled.json()["phase"] == "CANCELLED"
    _teardown()


async def test_clarify_endpoint(client):
    _wire([])
    created = await client.post(
        "/api/agent/tasks",
        json={"objective": "x", "userRequest": "x"},
    )
    task_id = created.json()["id"]
    assert created.json()["phase"] == "WAITING_FOR_AUTHORIZATION"

    clarified = await client.post(
        f"/api/agent/tasks/{task_id}/clarify", json={"answer": "Target is example.test"}
    )
    assert clarified.json()["phase"] == "PLANNING"
    _teardown()


async def test_list_tasks_endpoint(client):
    _wire([])
    await client.post(
        "/api/agent/tasks",
        json={"objective": "a", "userRequest": "a", "authorizationStatus": "AUTHORIZED"},
    )
    await client.post(
        "/api/agent/tasks",
        json={"objective": "b", "userRequest": "b", "authorizationStatus": "AUTHORIZED"},
    )
    listing = await client.get("/api/agent/tasks")
    assert len(listing.json()) == 2
    _teardown()


async def test_events_endpoint_returns_recorded_events(client):
    _wire([decision("CHECK_ENVIRONMENT"), decision("COMPLETE_TASK")])
    created = await client.post(
        "/api/agent/tasks",
        json={"objective": "x", "userRequest": "x", "authorizationStatus": "AUTHORIZED"},
    )
    task_id = created.json()["id"]
    await client.post(f"/api/agent/tasks/{task_id}/step", json={})

    events = await client.get(f"/api/agent/tasks/{task_id}/events")
    assert events.status_code == 200
    event_types = [e["eventType"] for e in events.json()]
    assert "AGENT_STARTED" in event_types
    _teardown()


async def test_malformed_decision_returns_task_blocked_not_500(client):
    _wire([{"garbage": True}])
    created = await client.post(
        "/api/agent/tasks",
        json={"objective": "x", "userRequest": "x", "authorizationStatus": "AUTHORIZED"},
    )
    task_id = created.json()["id"]
    step = await client.post(f"/api/agent/tasks/{task_id}/step", json={})
    assert step.status_code == 200
    assert step.json()["phase"] == "BLOCKED"
    _teardown()


async def test_no_unrestricted_execute_endpoint_exists(client):
    """Regression guard: the agent API must never expose raw command
    execution — every action still goes through policy/approval."""
    response = await client.post("/api/agent/execute", json={})
    assert response.status_code == 404

    paths = {getattr(r, "path", "") for r in agent_routes.router.routes}
    assert not any(p.endswith("/execute") for p in paths)
