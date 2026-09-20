import asyncio

import pytest
from services.policy.engine import PolicyDecision, PolicyVerdict
from services.terminal.audit import (
    COMMAND_APPROVED,
    COMMAND_COMPLETED,
    COMMAND_REJECTED,
    COMMAND_REQUESTED,
    COMMAND_STARTED,
    COMMAND_TIMEOUT,
    SESSION_CREATED,
)
from services.terminal.config import TerminalEngineConfig
from services.terminal.engine import TerminalEngine
from services.terminal.errors import UnsupportedPlatformError
from services.terminal.models import CommandStatus, TerminalCommandRequest
from services.terminal.platform_select import select_adapter
from services.terminal.platform_types import PlatformIdentifier

from tests.terminal.helpers import RecordingAuditSink, python_command

ALLOW = PolicyDecision(verdict=PolicyVerdict.ALLOW, reasons=["ok"])
DENY = PolicyDecision(verdict=PolicyVerdict.DENY, reasons=["not authorized"])
REQUIRE_APPROVAL = PolicyDecision(
    verdict=PolicyVerdict.REQUIRE_APPROVAL, reasons=["needs approval"], requires_approval=True
)


def _engine(**config_overrides) -> tuple[TerminalEngine, RecordingAuditSink]:
    sink = RecordingAuditSink()
    config = TerminalEngineConfig(**config_overrides)
    return TerminalEngine(config=config, audit_sink=sink), sink


async def test_allowed_command_executes_and_captures_stdout():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('hello-from-test')"),
        authorization_context=ALLOW,
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.COMPLETED
    assert result.exit_code == 0
    assert "hello-from-test" in result.stdout


async def test_stderr_is_captured_separately():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("import sys; sys.stderr.write('boom')"),
        authorization_context=ALLOW,
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.COMPLETED
    assert "boom" in result.stderr
    assert result.stdout == ""


async def test_non_zero_exit_code_is_reported():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("import sys; sys.exit(7)"),
        authorization_context=ALLOW,
    )

    result = await engine.execute(request)

    assert result.exit_code == 7
    assert result.status == CommandStatus.FAILED


async def test_denied_authorization_never_starts_a_process():
    engine, sink = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("open('/tmp/should-not-run', 'w').close()"),
        authorization_context=DENY,
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.REJECTED
    assert COMMAND_STARTED not in sink.event_types
    assert COMMAND_REJECTED in sink.event_types


async def test_require_approval_without_approval_is_rejected():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('should not run')"),
        authorization_context=REQUIRE_APPROVAL,
        approved_by_user=False,
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.REJECTED


async def test_require_approval_with_explicit_approval_executes():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('approved-run')"),
        authorization_context=REQUIRE_APPROVAL,
        approved_by_user=True,
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.COMPLETED
    assert "approved-run" in result.stdout


async def test_timeout_terminates_a_long_running_command():
    engine, sink = _engine(default_timeout_seconds=1)
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("import time; time.sleep(30)"),
        authorization_context=ALLOW,
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.TIMEOUT
    assert COMMAND_TIMEOUT in sink.event_types


async def test_cancellation_stops_a_running_command():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("import time; time.sleep(30)"),
        authorization_context=ALLOW,
    )

    execute_task = asyncio.create_task(engine.execute(request))
    await asyncio.sleep(0.2)  # let the process actually start
    terminated = await engine.terminate(request.id)
    result = await execute_task

    assert terminated is True
    assert result.status == CommandStatus.CANCELLED


async def test_output_limit_truncates_large_stdout():
    engine, _ = _engine(max_stdout_bytes=10)
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('x' * 10000)"),
        authorization_context=ALLOW,
    )

    result = await engine.execute(request)

    assert result.stdout_truncated is True
    assert len(result.stdout) <= 10


async def test_working_directory_traversal_is_rejected():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('hi')"),
        authorization_context=ALLOW,
        working_directory="../../etc",
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.REJECTED


async def test_secret_like_environment_overrides_are_filtered():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("import os; print(repr(os.environ.get('MY_SECRET_TOKEN')))"),
        authorization_context=ALLOW,
        environment={"MY_SECRET_TOKEN": "should-not-appear"},
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.COMPLETED
    assert "should-not-appear" not in result.stdout
    assert "None" in result.stdout


async def test_process_creation_failure_is_reported_without_leaking_internals():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=["definitely-not-a-real-executable-xyz"],
        authorization_context=ALLOW,
    )

    result = await engine.execute(request)

    assert result.status == CommandStatus.FAILED
    assert "Traceback" not in (result.stderr or "")


async def test_unsupported_platform_raises_from_adapter_selection(monkeypatch):
    import services.terminal.platform_select as platform_select_module

    monkeypatch.setattr(
        platform_select_module, "detect_platform", lambda: PlatformIdentifier.UNKNOWN
    )
    with pytest.raises(UnsupportedPlatformError):
        select_adapter()


_GENERIC_ENGINE_EVENTS = {
    SESSION_CREATED,
    COMMAND_REQUESTED,
    COMMAND_APPROVED,
    COMMAND_STARTED,
    COMMAND_COMPLETED,
}


async def test_audit_events_recorded_in_order_for_successful_run():
    """The engine's own (platform-independent) event sequence, filtered out
    from whatever extra platform-specific events (e.g. linux.session.created
    on this host, windows.* elsewhere) the auto-detected adapter also
    emits — see test_linux_adapter.py / test_windows_adapter.py for those."""
    engine, sink = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('ok')"),
        authorization_context=ALLOW,
    )

    await engine.execute(request)

    generic_events = [e for e in sink.event_types if e in _GENERIC_ENGINE_EVENTS]
    assert generic_events == [
        SESSION_CREATED,
        COMMAND_REQUESTED,
        COMMAND_APPROVED,
        COMMAND_STARTED,
        COMMAND_COMPLETED,
    ]


async def test_audit_events_never_include_raw_environment_secret():
    engine, sink = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('ok')"),
        authorization_context=ALLOW,
        environment={"MY_API_KEY": "super-secret-value"},
    )

    await engine.execute(request)

    for event in sink.events:
        assert "super-secret-value" not in str(event.data)


async def test_invalid_request_id_not_left_in_running_registry_after_failure():
    engine, _ = _engine()
    session = engine.create_session()
    request = TerminalCommandRequest(
        session_id=session.id,
        command=["definitely-not-a-real-executable-xyz"],
        authorization_context=ALLOW,
    )

    await engine.execute(request)

    assert request.id not in engine._running  # noqa: SLF001 - white-box cleanup check
