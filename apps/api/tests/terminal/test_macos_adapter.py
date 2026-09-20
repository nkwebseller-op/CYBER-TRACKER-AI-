"""macOS Terminal Adapter tests.

Runs entirely as harmless, cross-platform commands (the running Python
interpreter itself — see tests/terminal/helpers.py), since this sandbox is
Linux, not macOS. Everything genuinely macOS-specific (Darwin platform
detection, zsh discovery on a real system) is either mocked or isolated
into a single real-hardware integration test, marked skipif and only run
on actual macOS (`platform.system() == "Darwin"`).
"""

import asyncio
import os
import platform

import pytest
from services.terminal.adapters.base import CommandSpec, ExecutionStatus
from services.terminal.adapters.macos import (
    MACOS_COMMAND_CANCELLED,
    MACOS_COMMAND_COMPLETED,
    MACOS_COMMAND_FAILED,
    MACOS_COMMAND_STARTED,
    MACOS_COMMAND_TIMEOUT,
    MACOS_SESSION_CREATED,
    MacOSTerminalAdapter,
    resolve_macos_shell,
)
from services.terminal.audit import SESSION_CREATED
from services.terminal.config import TerminalEngineConfig
from services.terminal.engine import TerminalEngine
from services.terminal.platform_types import PlatformIdentifier, detect_platform

from tests.terminal.helpers import RecordingAuditSink, python_command


def _spec(argv: list[str], **overrides) -> CommandSpec:
    defaults = {"argv": argv, "timeout_seconds": 10}
    defaults.update(overrides)
    return CommandSpec(**defaults)


# --- platform detection -------------------------------------------------


def test_macos_is_detected_as_darwin(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.delenv("PREFIX", raising=False)
    assert detect_platform() == PlatformIdentifier.MACOS


def test_macos_is_never_confused_with_linux_windows_or_termux(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.delenv("PREFIX", raising=False)
    identifier = detect_platform()
    assert identifier == PlatformIdentifier.MACOS
    assert identifier != PlatformIdentifier.LINUX
    assert identifier != PlatformIdentifier.WINDOWS
    assert identifier != PlatformIdentifier.ANDROID_TERMUX


# --- shell resolution / capabilities -----------------------------------


def test_resolve_shell_prefers_env_shell(monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("shutil.which", lambda name: name if name == "/bin/zsh" else None)
    monkeypatch.setattr("os.path.isfile", lambda path: path == "/bin/zsh")
    assert resolve_macos_shell() == "/bin/zsh"


def test_resolve_shell_prefers_zsh_over_bash_and_sh(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: f"/bin/{name}" if name == "zsh" else None)
    assert resolve_macos_shell() == "/bin/zsh"


def test_resolve_shell_falls_back_to_bash_when_zsh_unavailable(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/bin/bash" if name == "bash" else None)
    assert resolve_macos_shell() == "/bin/bash"


def test_resolve_shell_falls_back_to_sh_when_zsh_and_bash_unavailable(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/bin/sh" if name == "sh" else None)
    assert resolve_macos_shell() == "/bin/sh"


def test_resolve_shell_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_macos_shell() is None


def test_resolve_shell_honors_configured_path(monkeypatch, tmp_path):
    configured = tmp_path / "custom-shell"
    configured.write_text("#!/bin/sh\n")
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_macos_shell(str(configured)) == str(configured)


def test_resolve_shell_rejects_nonexistent_configured_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert resolve_macos_shell("/definitely/not/a/real/path") is None


def test_capabilities_reflect_actual_availability_not_hardcoded(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    adapter = MacOSTerminalAdapter()
    caps = adapter.get_capabilities()

    assert caps.platform == "MACOS"
    assert caps.shell == "UNAVAILABLE"
    assert caps.shell_available is False
    assert caps.supports_streaming is True
    assert caps.supports_cancellation is True
    assert caps.supports_timeout is True


def test_capabilities_report_shell_when_available(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/bin/zsh" if name == "zsh" else None)
    caps = MacOSTerminalAdapter().get_capabilities()
    assert caps.shell == "/bin/zsh"
    assert caps.shell_available is True


# --- execution ---------------------------------------------------------------


async def test_run_success_emits_started_and_completed_events():
    adapter = MacOSTerminalAdapter()
    sink = RecordingAuditSink()
    ctx = {"session_id": "s1", "command_id": "c1", "task_id": "t1"}

    result = await adapter.run(
        _spec(python_command("print('macos-adapter-ok')")), audit=sink, context=ctx
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.exit_code == 0
    assert "macos-adapter-ok" in result.stdout
    assert sink.event_types == [MACOS_COMMAND_STARTED, MACOS_COMMAND_COMPLETED]
    assert all(e.session_id == "s1" and e.command_id == "c1" for e in sink.events)


async def test_run_failure_emits_failed_event():
    adapter = MacOSTerminalAdapter()
    sink = RecordingAuditSink()

    result = await adapter.run(
        _spec(python_command("import sys; sys.exit(3)")), audit=sink, context={}
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.exit_code == 3
    assert sink.event_types == [MACOS_COMMAND_STARTED, MACOS_COMMAND_FAILED]


async def test_run_without_audit_sink_still_works():
    adapter = MacOSTerminalAdapter()
    result = await adapter.run(_spec(python_command("print('ok')")))
    assert result.status == ExecutionStatus.SUCCEEDED


async def test_stdout_and_stderr_are_captured_separately():
    adapter = MacOSTerminalAdapter()
    result = await adapter.run(
        _spec(python_command("import sys; sys.stdout.write('out'); sys.stderr.write('err')"))
    )
    assert result.stdout == "out"
    assert result.stderr == "err"


async def test_start_and_end_timestamps_are_recorded():
    adapter = MacOSTerminalAdapter()
    result = await adapter.run(_spec(python_command("print('ok')")))
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.finished_at >= result.started_at


async def test_working_directory_is_respected(tmp_path):
    adapter = MacOSTerminalAdapter()
    result = await adapter.run(
        _spec(python_command("import os; print(os.getcwd())"), working_dir=str(tmp_path))
    )
    assert str(tmp_path) in result.stdout


async def test_invalid_working_directory_returns_failed_without_raising():
    adapter = MacOSTerminalAdapter()
    result = await adapter.run(
        _spec(python_command("print('should-not-run')"), working_dir="/definitely/not/a/dir-xyz")
    )
    assert result.status == ExecutionStatus.FAILED
    assert "Traceback" not in (result.stderr or "")


async def test_environment_allowlist_hides_unlisted_variables(monkeypatch):
    monkeypatch.setenv("CYBERAI_TEST_SECRET", "super-secret-value")
    adapter = MacOSTerminalAdapter()
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
    adapter = MacOSTerminalAdapter()
    sink = RecordingAuditSink()

    script = f"import time; time.sleep(2); open({str(marker)!r}, 'w').close()"
    result = await adapter.run(
        _spec(python_command(script), timeout_seconds=0.2), audit=sink, context={}
    )

    assert result.timed_out is True
    assert MACOS_COMMAND_TIMEOUT in sink.event_types
    await asyncio.sleep(2.2)
    assert not marker.exists(), "process was not actually killed on timeout — orphan process"


async def test_cancellation_kills_process_and_emits_cancelled_event(tmp_path):
    marker = tmp_path / "should-not-exist-either"
    adapter = MacOSTerminalAdapter()
    sink = RecordingAuditSink()

    script = f"import time; time.sleep(2); open({str(marker)!r}, 'w').close()"
    run_task = asyncio.create_task(
        adapter.run(_spec(python_command(script), timeout_seconds=30), audit=sink, context={})
    )
    await asyncio.sleep(0.2)
    run_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await run_task

    assert MACOS_COMMAND_CANCELLED in sink.event_types
    await asyncio.sleep(2.2)
    assert not marker.exists(), "process was not actually killed on cancellation — orphan process"


async def test_process_creation_failure_returns_failed_without_raising():
    adapter = MacOSTerminalAdapter()
    result = await adapter.run(_spec(["definitely-not-a-real-executable-xyz"]))
    assert result.status == ExecutionStatus.FAILED
    assert "Traceback" not in (result.stderr or "")


async def test_output_limit_truncation_is_respected():
    adapter = MacOSTerminalAdapter()
    result = await adapter.run(_spec(python_command("print('x' * 10000)"), max_stdout_bytes=10))
    assert result.stdout_truncated is True
    assert len(result.stdout) <= 10


# --- process-group cleanup ----------------------------------------------------


async def test_terminate_falls_back_to_base_kill_when_process_group_unavailable(monkeypatch):
    adapter = MacOSTerminalAdapter()
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


# --- authorization / malformed-request boundary (engine-enforced) ----------


async def test_authorization_rejection_never_reaches_the_adapter():
    """The adapter itself has no authorization logic — DENY must be
    rejected upstream by the engine's policy check, before `run()` is ever
    called. See test_engine.py::test_denied_authorization_never_starts_a_process
    for the full engine-level assertion; this only re-confirms the
    adapter has no independent path to bypass that boundary."""
    adapter = MacOSTerminalAdapter()
    assert not hasattr(adapter, "authorize")
    assert not hasattr(adapter, "is_authorized")


# --- engine integration: macOS gets its own session-created event ----------


async def test_engine_emits_macos_session_created_alongside_generic_event():
    sink = RecordingAuditSink()
    engine = TerminalEngine(
        config=TerminalEngineConfig(), adapter=MacOSTerminalAdapter(), audit_sink=sink
    )
    assert engine._platform_of(MacOSTerminalAdapter()) == PlatformIdentifier.MACOS  # noqa: SLF001

    engine.create_session(task_id="task-1")

    assert sink.event_types == [SESSION_CREATED, MACOS_SESSION_CREATED]


# --- real macOS integration (only runs on actual macOS hardware) -----------


@pytest.mark.skipif(platform.system() != "Darwin", reason="real macOS shell integration test")
async def test_real_shell_execution_on_macos():
    adapter = MacOSTerminalAdapter()
    shell = adapter.resolve_shell()
    assert shell is not None
    result = await adapter.run(_spec(python_command("print('cyberai-macos-ok')")))
    assert result.status == ExecutionStatus.SUCCEEDED
    assert "cyberai-macos-ok" in result.stdout
