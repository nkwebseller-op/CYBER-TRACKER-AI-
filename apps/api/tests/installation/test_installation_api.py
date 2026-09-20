from uuid import uuid4

from services.installation.config import InstallationServiceConfig
from services.installation.environment import EnvironmentInspector
from services.installation.models import EnvironmentCheck, PackageManager
from services.installation.registry import InMemoryInstallationRegistry
from services.installation.service import ToolInstallationService
from services.policy.engine import RiskTier
from services.terminal.engine import TerminalEngine
from services.tools.registry import InMemoryToolRegistry

from app.api.routes import installation as installation_routes
from app.core.installation import get_installation_service
from app.core.terminal_engine import get_terminal_engine
from app.core.tools import get_tool_registry
from app.db.session import get_db
from app.main import app
from tests.installation.helpers import ScriptedAdapter, approved_tool, success_result


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


class _FixedEnvironment(EnvironmentInspector):
    def inspect(self, *, identifier=None):
        return EnvironmentCheck(
            platform="LINUX",
            architecture="x86_64",
            shell="/bin/bash",
            available_package_managers=(PackageManager.APT,),
        )


def _wire(*, adapter_results=None, target_active=True):
    tools = InMemoryToolRegistry()
    installations = InMemoryInstallationRegistry()
    adapter = ScriptedAdapter(adapter_results or [])
    engine = TerminalEngine(adapter=adapter)
    service = ToolInstallationService(
        tools=tools,
        installations=installations,
        environment_inspector=_FixedEnvironment(),
        config=InstallationServiceConfig(max_install_attempts=1),
    )

    target_id = uuid4()
    target = _FakeTarget(target_id, is_active=target_active)

    async def fake_get_db():
        yield _FakeDBSession(target)

    app.dependency_overrides[get_installation_service] = lambda: service
    app.dependency_overrides[get_tool_registry] = lambda: tools
    app.dependency_overrides[get_terminal_engine] = lambda: engine
    app.dependency_overrides[get_db] = fake_get_db
    return tools, target_id


def _teardown():
    for dep in (get_installation_service, get_tool_registry, get_terminal_engine, get_db):
        app.dependency_overrides.pop(dep, None)


async def test_readiness_endpoint_reports_ready(client):
    tools, target_id = _wire()
    tool = await tools.create(approved_tool())

    response = await client.get(
        "/api/installations/readiness",
        params={"tool_id": str(tool.id), "target_id": str(target_id), "platform": "LINUX"},
    )

    assert response.status_code == 200
    assert response.json()["ready"] is True
    _teardown()


async def test_readiness_endpoint_unknown_target_returns_404(client):
    tools, _target_id = _wire()
    tool = await tools.create(approved_tool())

    response = await client.get(
        "/api/installations/readiness",
        params={"tool_id": str(tool.id), "target_id": str(uuid4()), "platform": "LINUX"},
    )

    assert response.status_code == 404
    _teardown()


async def test_request_installation_waits_for_approval(client):
    tools, target_id = _wire()
    tool = await tools.create(approved_tool())

    response = await client.post(
        "/api/installations",
        json={"toolId": str(tool.id), "targetId": str(target_id), "platform": "LINUX"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "WAITING_FOR_APPROVAL"
    assert body["plan"]["packageManager"] == "apt"
    _teardown()


async def test_request_installation_blocked_for_inactive_target(client):
    tools, target_id = _wire(target_active=False)
    tool = await tools.create(approved_tool())

    response = await client.post(
        "/api/installations",
        json={"toolId": str(tool.id), "targetId": str(target_id), "platform": "LINUX"},
    )

    assert response.status_code == 201
    assert response.json()["state"] == "BLOCKED"
    _teardown()


async def test_full_flow_approve_start_install(client):
    tools, target_id = _wire(
        adapter_results=[success_result("installed"), success_result("dig 9.18")]
    )
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))

    created = await client.post(
        "/api/installations",
        json={"toolId": str(tool.id), "targetId": str(target_id), "platform": "LINUX"},
    )
    request_id = created.json()["id"]
    assert created.json()["state"] == "PREPARING"  # low risk, no approval needed

    started = await client.post(
        f"/api/installations/{request_id}/start", json={"targetId": str(target_id)}
    )

    assert started.status_code == 200
    body = started.json()
    assert body["state"] == "INSTALLED"
    assert body["verification"]["verified"] is True
    _teardown()


async def test_approve_endpoint_transitions_state(client):
    tools, target_id = _wire()
    tool = await tools.create(approved_tool())  # MEDIUM risk -> requires approval

    created = await client.post(
        "/api/installations",
        json={"toolId": str(tool.id), "targetId": str(target_id), "platform": "LINUX"},
    )
    request_id = created.json()["id"]

    approved = await client.post(
        f"/api/installations/{request_id}/approve", json={"approvedBy": "ops@example.com"}
    )
    assert approved.status_code == 200
    assert approved.json()["state"] == "PREPARING"
    _teardown()


async def test_start_without_approval_returns_409(client):
    tools, target_id = _wire()
    tool = await tools.create(approved_tool())

    created = await client.post(
        "/api/installations",
        json={"toolId": str(tool.id), "targetId": str(target_id), "platform": "LINUX"},
    )
    request_id = created.json()["id"]

    started = await client.post(
        f"/api/installations/{request_id}/start", json={"targetId": str(target_id)}
    )
    assert started.status_code == 409
    _teardown()


async def test_reject_endpoint(client):
    tools, target_id = _wire()
    tool = await tools.create(approved_tool())

    created = await client.post(
        "/api/installations",
        json={"toolId": str(tool.id), "targetId": str(target_id), "platform": "LINUX"},
    )
    request_id = created.json()["id"]

    rejected = await client.post(
        f"/api/installations/{request_id}/reject", json={"reason": "Not authorized this week."}
    )
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "CANCELLED"
    _teardown()


async def test_get_unknown_installation_returns_404(client):
    _wire()
    response = await client.get(f"/api/installations/{uuid4()}")
    assert response.status_code == 404
    _teardown()


async def test_list_installations_and_installed(client):
    tools, target_id = _wire(
        adapter_results=[success_result("installed"), success_result("dig 9.18")]
    )
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))

    created = await client.post(
        "/api/installations",
        json={"toolId": str(tool.id), "targetId": str(target_id), "platform": "LINUX"},
    )
    request_id = created.json()["id"]
    await client.post(f"/api/installations/{request_id}/start", json={"targetId": str(target_id)})

    all_requests = await client.get("/api/installations")
    assert len(all_requests.json()) == 1

    installed = await client.get("/api/installations/installed")
    assert len(installed.json()) == 1
    assert installed.json()[0]["state"] == "INSTALLED"
    _teardown()


async def test_no_unrestricted_execute_endpoint_exists(client):
    """Regression guard: this phase must never introduce a raw shell/argv
    execution endpoint alongside the installation flow."""
    response = await client.post("/api/installations/execute", json={})
    assert response.status_code in (404, 405, 422)

    paths = {getattr(r, "path", "") for r in installation_routes.router.routes}
    assert not any(p.endswith("/execute") for p in paths)
