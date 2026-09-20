"""Linux Terminal Adapter tests.

Runs entirely as harmless, cross-platform commands (the running Python
interpreter itself — see tests/terminal/helpers.py). Process-group
termination via os.killpg is exercised for real on this Linux CI sandbox;
anything that would only differ on other POSIX systems is mocked.
"""

import asyncio
import os

import pytest
from services.terminal.adapters.base import CommandSpec, ExecutionStatus
from services.terminal.adapters.linux import (
    LINUX_COMMAND_CANCELLED,
    LINUX_COMMAND_COMPLETED,
    LINUX_COMMAND_FAILED,
    LINUX_COMMAND_STARTED,
    LINUX_COMMAND_TIMEOUT,
    LINUX_SESSION_CREATED,
    LinuxTerminalAdapter,
    resolve_linux_shell,
)
from services.terminal.audit import SESSION_CREATED
from services.terminal.config import TerminalEngineConfig
from services.terminal.engine import TerminalEngine
from services.terminal.platform_types import PlatformIdentifier

from tests.terminal.helpers import RecordingAuditSink, python_command


def _spec(argv: list[str], **overrides) -> CommandSpec:
    defaults = {"argv": argv, "timeout_seconds": 10}
    defaults.update(overrides)
    return CommandSpec(**defaults)


# --- shell resolution / capabilities -----------------------------------


def test_resolve_shell_prefers_env_shell(monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("shutil.which", lambda name: name if name == "/bin/zsh" else None)
    monkeypatch.setattr("os.path.isfile", lambda path: path == "/bin/zsh")
    assert resolve_linux_shell() == "/bin/zsh"


def test_resolve_shell_falls_back_to_bash_then_sh(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/bin/bash" if name == "bash" else None)
    assert resolve_linux_shell() == "/bin/bash"


def test_resolve_shell_falls_back_to_sh_when_bash_unavailable(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/bin/sh" if name == "sh" else None)
    assert resolve_linux_shell() == "/bin/sh"


def test_resolve_shell_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_linux_shell() is None


def test_resolve_shell_honors_configured_path(monkeypatch, tmp_path):
    configured = tmp_path / "custom-shell"
    configured.write_text("#!/bin/sh\n")
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_linux_shell(str(configured)) == str(configured)


def test_resolve_shell_rejects_nonexistent_configured_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_linux_shell("/definitely/not/a/real/path") is None


def test_capabilities_reflect_actual_availability_not_hardcoded(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    adapter = LinuxTerminalAdapter()
    caps = adapter.get_capabilities()

    assert caps.platform == "LINUX"
    assert caps.shell == "UNAVAILABLE"
    assert caps.shell_available is False
    assert caps.supports_streaming is True
    assert caps.supports_cancellation is True
    assert caps.supports_timeout is True


def test_capabilities_report_shell_when_available(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/bin/bash" if name == "bash" else None)
    caps = LinuxTerminalAdapter().get_capabilities()
    assert caps.shell == "/bin/bash"
    assert caps.shell_available is True


# --- execution ---------------------------------------------------------------


async def test_run_success_emits_started_and_completed_events():
    adapter = LinuxTerminalAdapter()
    sink = RecordingAuditSink()
    ctx = {"session_id": "s1", "command_id": "c1", "task_id": "t1"}

    result = await adapter.run(
        _spec(python_command("print('linux-adapter-ok')")), audit=sink, context=ctx
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.exit_code == 0
    assert "linux-adapter-ok" in result.stdout
    assert sink.event_types == [LINUX_COMMAND_STARTED, LINUX_COMMAND_COMPLETED]
    assert all(e.session_id == "s1" and e.command_id == "c1" for e in sink.events)


async def test_run_failure_emits_failed_event():
    adapter = LinuxTerminalAdapter()
    sink = RecordingAuditSink()

    result = await adapter.run(
        _spec(python_command("import sys; sys.exit(3)")), audit=sink, context={}
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.exit_code == 3
    assert sink.event_types == [LINUX_COMMAND_STARTED, LINUX_COMMAND_FAILED]


async def test_run_without_audit_sink_still_works():
    adapter = LinuxTerminalAdapter()
    result = await adapter.run(_spec(python_command("print('ok')")))
    assert result.status == ExecutionStatus.SUCCEEDED


async def test_stdout_and_stderr_are_captured_separately():
    adapter = LinuxTerminalAdapter()
    result = await adapter.run(
        _spec(python_command("import sys; sys.stdout.write('out'); sys.stderr.write('err')"))
    )
    assert result.stdout == "out"
    assert result.stderr == "err"


async def test_working_directory_is_respected(tmp_path):
    adapter = LinuxTerminalAdapter()
    result = await adapter.run(
        _spec(python_command("import os; print(os.getcwd())"), working_dir=str(tmp_path))
    )
    assert str(tmp_path) in result.stdout


async def test_invalid_working_directory_returns_failed_without_raising():
    adapter = LinuxTerminalAdapter()
    result = await adapter.run(
        _spec(python_command("print('should-not-run')"), working_dir="/definitely/not/a/dir-xyz")
    )
    assert result.status == ExecutionStatus.FAILED
    assert "Traceback" not in (result.stderr or "")


async def test_environment_allowlist_hides_unlisted_variables(monkeypatch):
    monkeypatch.setenv("CYBERAI_TEST_SECRET", "super-secret-value")
    adapter = LinuxTerminalAdapter()
    result = await adapter.run(
        _spec(
            python_command("import os; print(os.environ.get('CYBERAI_TEST_SECRET', 'MISSING'))"),
            env_allowlist=(),
        )
    )
    assert "super-secret-value" not in result.stdout
    assert "MISSING" in result.stdout


# --- timeout / cancellation: must not leave orphan processes -----------------


async def test_timeout_kills_process_and_emits_timeout_event(tmp_path):
    marker = tmp_path / "should-not-exist"
    adapter = LinuxTerminalAdapter()
    sink = RecordingAuditSink()

    script = f"import time; time.sleep(2); open({str(marker)!r}, 'w').close()"
    result = await adapter.run(
        _spec(python_command(script), timeout_seconds=0.2), audit=sink, context={}
    )

    assert result.timed_out is True
    assert LINUX_COMMAND_TIMEOUT in sink.event_types
    await asyncio.sleep(2.2)
    assert not marker.exists(), "process was not actually killed on timeout — orphan process"


async def test_cancellation_kills_process_and_emits_cancelled_event(tmp_path):
    marker = tmp_path / "should-not-exist-either"
    adapter = LinuxTerminalAdapter()
    sink = RecordingAuditSink()

    script = f"import time; time.sleep(2); open({str(marker)!r}, 'w').close()"
    run_task = asyncio.create_task(
        adapter.run(_spec(python_command(script), timeout_seconds=30), audit=sink, context={})
    )
    await asyncio.sleep(0.2)
    run_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await run_task

    assert LINUX_COMMAND_CANCELLED in sink.event_types
    await asyncio.sleep(2.2)
    assert not marker.exists(), "process was not actually killed on cancellation — orphan process"


async def test_process_creation_failure_returns_failed_without_raising():
    adapter = LinuxTerminalAdapter()
    result = await adapter.run(_spec(["definitely-not-a-real-executable-xyz"]))
    assert result.status == ExecutionStatus.FAILED
    assert "Traceback" not in (result.stderr or "")


async def test_output_limit_truncation_is_respected():
    adapter = LinuxTerminalAdapter()
    result = await adapter.run(_spec(python_command("print('x' * 10000)"), max_stdout_bytes=10))
    assert result.stdout_truncated is True
    assert len(result.stdout) <= 10


# --- process-group cleanup ----------------------------------------------------


async def test_terminate_falls_back_to_base_kill_when_process_group_unavailable(monkeypatch):
    adapter = LinuxTerminalAdapter()
    monkeypatch.delattr(os, "killpg", raising=False)

    killed = []

    class FakeProcess:
        pid = 4242
        returncode = None

        def kill(self):
            killed.append(True)

        async def wait(self):
            return None

    await adapter._terminate(FakeProcess())
    assert killed == [True]


# --- engine integration: Linux gets its own session-created event -----------


async def test_engine_emits_linux_session_created_alongside_generic_event():
    sink = RecordingAuditSink()
    engine = TerminalEngine(
        config=TerminalEngineConfig(), adapter=LinuxTerminalAdapter(), audit_sink=sink
    )
    monkeypatch_platform = engine._platform_of  # noqa: SLF001
    assert monkeypatch_platform(LinuxTerminalAdapter()) == PlatformIdentifier.LINUX

    engine.create_session(task_id="task-1")

    assert sink.event_types == [SESSION_CREATED, LINUX_SESSION_CREATED]
