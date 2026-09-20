"""Windows Terminal Adapter tests.

Runs entirely on non-Windows CI using harmless, cross-platform commands
(the running Python interpreter itself — see tests/terminal/helpers.py) and
mocks for anything genuinely Windows-only (taskkill, PowerShell discovery).
A single real-Windows integration test is marked skipif and will only run
where os.name == "nt".
"""

import asyncio
import os

import pytest
from services.terminal.adapters.base import CommandSpec, ExecutionStatus
from services.terminal.adapters.linux import LinuxAdapter
from services.terminal.adapters.macos import MacOSAdapter
from services.terminal.adapters.termux import TermuxAdapter
from services.terminal.adapters.windows import (
    WINDOWS_COMMAND_CANCELLED,
    WINDOWS_COMMAND_COMPLETED,
    WINDOWS_COMMAND_FAILED,
    WINDOWS_COMMAND_STARTED,
    WINDOWS_COMMAND_TIMEOUT,
    WINDOWS_SESSION_CREATED,
    WindowsTerminalAdapter,
    resolve_powershell_executable,
)
from services.terminal.audit import SESSION_CREATED
from services.terminal.config import TerminalEngineConfig
from services.terminal.engine import TerminalEngine

from tests.terminal.helpers import RecordingAuditSink, python_command


def _spec(argv: list[str], **overrides) -> CommandSpec:
    defaults = {"argv": argv, "timeout_seconds": 10}
    defaults.update(overrides)
    return CommandSpec(**defaults)


# --- PowerShell resolution / capabilities -----------------------------------


def test_resolve_powershell_prefers_pwsh_over_legacy(monkeypatch):
    def fake_which(name):
        return f"/usr/bin/{name}" if name == "pwsh" else None

    monkeypatch.setattr("shutil.which", fake_which)
    assert resolve_powershell_executable() == "/usr/bin/pwsh"


def test_resolve_powershell_falls_back_to_powershell_exe(monkeypatch):
    def fake_which(name):
        return "/usr/bin/powershell.exe" if name == "powershell.exe" else None

    monkeypatch.setattr("shutil.which", fake_which)
    assert resolve_powershell_executable() == "/usr/bin/powershell.exe"


def test_resolve_powershell_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_powershell_executable() is None


def test_resolve_powershell_honors_configured_path(monkeypatch, tmp_path):
    configured = tmp_path / "custom-pwsh"
    configured.write_text("#!/bin/sh\n")
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_powershell_executable(str(configured)) == str(configured)


def test_resolve_powershell_rejects_nonexistent_configured_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_powershell_executable("/definitely/not/a/real/path") is None


def test_capabilities_reflect_actual_availability_not_hardcoded(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    adapter = WindowsTerminalAdapter()
    caps = adapter.get_capabilities()

    assert caps.platform == "WINDOWS"
    assert caps.shell == "UNAVAILABLE"
    assert caps.shell_available is False
    # These are true regardless of shell availability — they describe what
    # the *adapter* supports, not the shell.
    assert caps.supports_streaming is True
    assert caps.supports_cancellation is True
    assert caps.supports_timeout is True


def test_capabilities_report_powershell_when_available(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pwsh" if name == "pwsh" else None)
    caps = WindowsTerminalAdapter().get_capabilities()
    assert caps.shell == "POWERSHELL"
    assert caps.shell_available is True


def test_build_powershell_command_never_uses_shell_string_concatenation():
    script = "Write-Output 'hello'; Get-Location"
    argv = WindowsTerminalAdapter.build_powershell_command(script, powershell_path="/usr/bin/pwsh")

    assert isinstance(argv, list)
    assert argv[0] == "/usr/bin/pwsh"
    assert script in argv  # passed as one opaque argv element, never concatenated
    assert "-NonInteractive" in argv
    assert "-ExecutionPolicy" in argv


# --- execution ---------------------------------------------------------------


async def test_run_success_emits_started_and_completed_events():
    adapter = WindowsTerminalAdapter()
    sink = RecordingAuditSink()
    ctx = {"session_id": "s1", "command_id": "c1", "task_id": "t1"}

    result = await adapter.run(
        _spec(python_command("print('windows-adapter-ok')")), audit=sink, context=ctx
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.exit_code == 0
    assert "windows-adapter-ok" in result.stdout
    assert sink.event_types == [WINDOWS_COMMAND_STARTED, WINDOWS_COMMAND_COMPLETED]
    assert all(e.session_id == "s1" and e.command_id == "c1" for e in sink.events)


async def test_run_failure_emits_failed_event():
    adapter = WindowsTerminalAdapter()
    sink = RecordingAuditSink()

    result = await adapter.run(
        _spec(python_command("import sys; sys.exit(3)")), audit=sink, context={}
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.exit_code == 3
    assert sink.event_types == [WINDOWS_COMMAND_STARTED, WINDOWS_COMMAND_FAILED]


async def test_run_without_audit_sink_still_works():
    adapter = WindowsTerminalAdapter()
    result = await adapter.run(_spec(python_command("print('ok')")))
    assert result.status == ExecutionStatus.SUCCEEDED


async def test_stderr_is_captured():
    adapter = WindowsTerminalAdapter()
    result = await adapter.run(
        _spec(python_command("import sys; sys.stderr.write('bad')"))
    )
    assert "bad" in result.stderr
    assert result.stdout == ""


# --- timeout / cancellation: must not leave orphan processes -----------------


async def test_timeout_kills_process_and_emits_timeout_event(tmp_path):
    marker = tmp_path / "should-not-exist"
    adapter = WindowsTerminalAdapter()
    sink = RecordingAuditSink()

    script = f"import time; time.sleep(2); open({str(marker)!r}, 'w').close()"
    result = await adapter.run(
        _spec(python_command(script), timeout_seconds=0.2), audit=sink, context={}
    )

    assert result.timed_out is True
    assert WINDOWS_COMMAND_TIMEOUT in sink.event_types
    # Give the (killed) process time to have finished its sleep if it had
    # NOT actually been terminated, then confirm the marker never appears.
    await asyncio.sleep(2.2)
    assert not marker.exists(), "process was not actually killed on timeout — orphan process"


async def test_cancellation_kills_process_and_emits_cancelled_event(tmp_path):
    marker = tmp_path / "should-not-exist-either"
    adapter = WindowsTerminalAdapter()
    sink = RecordingAuditSink()

    script = f"import time; time.sleep(2); open({str(marker)!r}, 'w').close()"
    run_task = asyncio.create_task(
        adapter.run(_spec(python_command(script), timeout_seconds=30), audit=sink, context={})
    )
    await asyncio.sleep(0.2)  # let the process actually start
    run_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await run_task

    assert WINDOWS_COMMAND_CANCELLED in sink.event_types
    await asyncio.sleep(2.2)
    assert not marker.exists(), "process was not actually killed on cancellation — orphan process"


async def test_process_creation_failure_returns_failed_without_raising():
    adapter = WindowsTerminalAdapter()
    result = await adapter.run(_spec(["definitely-not-a-real-executable-xyz"]))
    assert result.status == ExecutionStatus.FAILED
    assert "Traceback" not in (result.stderr or "")


async def test_output_limit_truncation_is_respected():
    adapter = WindowsTerminalAdapter()
    result = await adapter.run(_spec(python_command("print('x' * 10000)"), max_stdout_bytes=10))
    assert result.stdout_truncated is True
    assert len(result.stdout) <= 10


# --- taskkill process-tree cleanup (simulated; real Windows API mocked) -----


async def test_terminate_attempts_taskkill_when_simulating_windows(monkeypatch):
    calls = []

    class FakeKillerProcess:
        async def wait(self):
            return None

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append(args)
        return FakeKillerProcess()

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    adapter = WindowsTerminalAdapter()

    class FakeProcess:
        pid = 4242
        returncode = None

        def kill(self):
            pass

        async def wait(self):
            return None

    await adapter._terminate(FakeProcess())

    assert len(calls) == 1
    assert calls[0][0] == "taskkill"
    assert "4242" in calls[0]
    assert "/T" in calls[0]
    assert "/F" in calls[0]


@pytest.mark.skipif(os.name != "nt", reason="real Windows/PowerShell integration test")
async def test_real_powershell_execution_on_windows():
    adapter = WindowsTerminalAdapter()
    shell = adapter.resolve_shell()
    assert shell is not None
    argv = WindowsTerminalAdapter.build_powershell_command(
        "Write-Output 'cyberai-windows-ok'", powershell_path=shell
    )
    result = await adapter.run(_spec(argv))
    assert result.status == ExecutionStatus.SUCCEEDED
    assert "cyberai-windows-ok" in result.stdout


# --- engine integration: Windows gets its own session-created event -------


async def test_engine_emits_windows_session_created_alongside_generic_event():
    sink = RecordingAuditSink()
    engine = TerminalEngine(
        config=TerminalEngineConfig(), adapter=WindowsTerminalAdapter(), audit_sink=sink
    )

    engine.create_session(task_id="task-1")

    assert sink.event_types == [SESSION_CREATED, WINDOWS_SESSION_CREATED]


# --- regression: other adapters are unaffected by the shared base changes --


@pytest.mark.parametrize("adapter_cls", [LinuxAdapter, MacOSAdapter, TermuxAdapter])
async def test_other_adapters_still_work_with_old_call_signature(adapter_cls):
    """Positional-only call (no audit/context) must keep working — this is
    exactly how these adapters were called before Phase 6."""
    adapter = adapter_cls()
    result = await adapter.run(_spec(python_command("print('still-fine')")))
    assert result.status == ExecutionStatus.SUCCEEDED
    assert "still-fine" in result.stdout
