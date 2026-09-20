"""Integration tests for the Terminal Engine API — exercised through the
real FastAPI routes, with the DB dependency swapped for an in-memory fake
Target lookup (no real database needed) and a real, in-process
TerminalEngine (harmless commands only, per services/terminal/command_templates.py).
"""

from uuid import uuid4

import pytest
from services.terminal.engine import TerminalEngine

from app.api.routes import terminal as terminal_routes
from app.core.terminal_engine import get_terminal_engine
from app.db.session import get_db
from app.main import app


class _FakeTarget:
    def __init__(self, target_id, *, is_active=True, expires_at=None):
        self.id = target_id
        self.is_active = is_active
        self.expires_at = expires_at


class _FakeDBSession:
    def __init__(self, target=None):
        self._target = target

    async def get(self, _model, target_id):
        if self._target is not None and self._target.id == target_id:
            return self._target
        return None


@pytest.fixture
def engine():
    return TerminalEngine()


@pytest.fixture(autouse=True)
def _override_engine(engine):
    app.dependency_overrides[get_terminal_engine] = lambda: engine
    yield
    app.dependency_overrides.pop(get_terminal_engine, None)
    app.dependency_overrides.pop(get_db, None)


def _override_db(target) -> None:
    async def _fake_get_db():
        yield _FakeDBSession(target)

    app.dependency_overrides[get_db] = _fake_get_db


async def test_create_session_returns_ready_session(client):
    response = await client.post("/api/terminal/sessions", json={"taskId": "task-1"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "READY"
    assert body["taskId"] == "task-1"


async def test_get_session_returns_current_status(client):
    created = await client.post("/api/terminal/sessions", json={})
    session_id = created.json()["id"]

    response = await client.get(f"/api/terminal/sessions/{session_id}")

    assert response.status_code == 200
    assert response.json()["id"] == session_id


async def test_get_unknown_session_returns_404(client):
    response = await client.get(f"/api/terminal/sessions/{uuid4()}")
    assert response.status_code == 404


async def test_execute_rejects_unregistered_action_type(client):
    target_id = uuid4()
    _override_db(_FakeTarget(target_id))
    session = (await client.post("/api/terminal/sessions", json={})).json()

    response = await client.post(
        "/api/terminal/execute",
        json={
            "sessionId": session["id"],
            "taskId": "task-1",
            "targetId": str(target_id),
            "actionType": "web.arbitrary_scan",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "action_not_registered"


async def test_execute_rejects_unknown_target(client):
    _override_db(None)
    session = (await client.post("/api/terminal/sessions", json={})).json()

    response = await client.post(
        "/api/terminal/execute",
        json={
            "sessionId": session["id"],
            "taskId": "task-1",
            "targetId": str(uuid4()),
            "actionType": "diagnostics.echo_test",
        },
    )

    assert response.status_code == 404


async def test_execute_rejects_inactive_target_without_running_anything(client, engine):
    target_id = uuid4()
    _override_db(_FakeTarget(target_id, is_active=False))
    session = (await client.post("/api/terminal/sessions", json={})).json()

    response = await client.post(
        "/api/terminal/execute",
        json={
            "sessionId": session["id"],
            "taskId": "task-1",
            "targetId": str(target_id),
            "actionType": "diagnostics.echo_test",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "policy_denied"


async def test_execute_registered_action_runs_and_returns_result(client):
    target_id = uuid4()
    _override_db(_FakeTarget(target_id))
    session = (await client.post("/api/terminal/sessions", json={})).json()

    response = await client.post(
        "/api/terminal/execute",
        json={
            "sessionId": session["id"],
            "taskId": "task-1",
            "targetId": str(target_id),
            "actionType": "diagnostics.echo_test",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["exitCode"] == 0
    assert "cyberai-terminal-engine-ok" in body["stdout"]


async def test_get_session_output_reflects_last_result(client):
    target_id = uuid4()
    _override_db(_FakeTarget(target_id))
    session = (await client.post("/api/terminal/sessions", json={})).json()

    await client.post(
        "/api/terminal/execute",
        json={
            "sessionId": session["id"],
            "taskId": "task-1",
            "targetId": str(target_id),
            "actionType": "diagnostics.echo_test",
        },
    )

    response = await client.get(f"/api/terminal/sessions/{session['id']}/output")

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


async def test_terminate_session_marks_it_stopped(client):
    session = (await client.post("/api/terminal/sessions", json={})).json()

    response = await client.post(f"/api/terminal/sessions/{session['id']}/terminate")

    assert response.status_code == 200
    assert response.json()["status"] == "STOPPED"


async def test_no_route_accepts_raw_command_text(client):
    """Regression guard: the execute contract has no field that could carry
    arbitrary shell text — only a reviewed `actionType` string."""
    fields = set(terminal_routes.ExecuteRequest.model_fields.keys())
    assert "command" not in fields
    assert "argv" not in fields
    assert "shell" not in fields
