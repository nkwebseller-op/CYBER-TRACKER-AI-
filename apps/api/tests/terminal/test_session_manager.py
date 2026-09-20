from datetime import UTC, datetime, timedelta

import pytest
from services.terminal.config import TerminalEngineConfig
from services.terminal.errors import InvalidRequestError, SessionExpiredError, SessionNotFoundError
from services.terminal.models import SessionStatus
from services.terminal.platform_types import PlatformIdentifier
from services.terminal.session_manager import SessionManager


def _manager(**overrides) -> SessionManager:
    config = TerminalEngineConfig(**overrides)
    return SessionManager(config)


def test_create_session_returns_ready_session():
    manager = _manager()
    session = manager.create_session(platform=PlatformIdentifier.LINUX, task_id="task-1")
    assert session.status == SessionStatus.READY
    assert session.platform == PlatformIdentifier.LINUX


def test_get_session_not_found_raises():
    manager = _manager()
    with pytest.raises(SessionNotFoundError):
        manager.get_session(__import__("uuid").uuid4())


def test_session_expires_after_ttl():
    manager = _manager(session_ttl_seconds=1)
    session = manager.create_session(platform=PlatformIdentifier.LINUX)
    session.last_activity_at = datetime.now(UTC) - timedelta(seconds=10)

    refreshed = manager.get_session(session.id)

    assert refreshed.status == SessionStatus.EXPIRED


def test_require_active_session_rejects_expired():
    manager = _manager(session_ttl_seconds=1)
    session = manager.create_session(platform=PlatformIdentifier.LINUX)
    session.last_activity_at = datetime.now(UTC) - timedelta(seconds=10)

    with pytest.raises(SessionExpiredError):
        manager.require_active_session(session.id)


def test_close_session_marks_stopped():
    manager = _manager()
    session = manager.create_session(platform=PlatformIdentifier.LINUX)
    closed = manager.close_session(session.id)
    assert closed.status == SessionStatus.STOPPED


def test_max_concurrent_sessions_enforced():
    manager = _manager(max_concurrent_sessions=1)
    manager.create_session(platform=PlatformIdentifier.LINUX)
    with pytest.raises(InvalidRequestError):
        manager.create_session(platform=PlatformIdentifier.LINUX)
