"""Linux Terminal Adapter.

    TerminalEngine
          |
    LinuxTerminalAdapter (this file)
          |
    Controlled Linux process (argv exec, never shell=True)
          |
    stdout / stderr -> TerminalCommandResult

Inherits all process-control machinery (timeout, output caps, env
allowlisting, cancellation-safe kill) from LocalProcessAdapter — the same
base every local-process adapter uses — and adds two Linux-specific
things:

1. Shell resolution/availability (`resolve_shell` / `get_capabilities`) —
   distribution-agnostic: prefers a configured path, then `$SHELL`, then
   probes for the common POSIX shells in order (`bash`, then `sh`). This
   is informational only: command templates supply argv directly, so no
   command execution actually depends on a shell being available.
2. Best-effort Linux process-group termination (`SIGTERM` to the whole
   process group via `os.killpg`, escalating to `SIGKILL`) on
   timeout/cancellation/output-limit-exceeded, falling back to the base
   class's plain `process.kill()` when the process wasn't started in its
   own group (or on any platform where process groups aren't available).

Nothing here decides whether a command is authorized — see
services/terminal/engine.py, which only ever calls `run()` after
`ApprovedExecution.from_policy_decision` has succeeded.
"""

import asyncio
import os
import shutil
import signal
from dataclasses import dataclass

from services.terminal.adapters.base import CommandSpec, ExecutionResult, ExecutionStatus
from services.terminal.adapters.local_process import LocalProcessAdapter
from services.terminal.audit import AuditEvent, AuditSink, truncate_for_log

LINUX_COMMAND_STARTED = "linux.command.started"
LINUX_COMMAND_COMPLETED = "linux.command.completed"
LINUX_COMMAND_FAILED = "linux.command.failed"
LINUX_COMMAND_TIMEOUT = "linux.command.timeout"
LINUX_COMMAND_CANCELLED = "linux.command.cancelled"
LINUX_SESSION_CREATED = "linux.session.created"

_CANDIDATE_SHELLS = ("bash", "sh")


@dataclass(frozen=True)
class LinuxCapabilities:
    """Reflects what this runtime can *actually* do — never hardcoded.
    `shell`/`shell_available` are computed by probing for a real
    executable at the moment of the call."""

    platform: str
    shell: str
    shell_available: bool
    supports_streaming: bool
    supports_cancellation: bool
    supports_timeout: bool


def resolve_linux_shell(preferred_path: str | None = None) -> str | None:
    """Distribution-agnostic shell resolution. Prefers a configured path,
    then `$SHELL` (the user/environment's own configured shell), then
    falls back to probing for common POSIX shells — never assumes a
    specific shell exists at a hardcoded path."""
    if preferred_path:
        resolved = shutil.which(preferred_path)
        if resolved:
            return resolved
        if os.path.isfile(preferred_path):
            return preferred_path
        return None  # an explicitly configured path that doesn't exist is not silently ignored

    env_shell = os.environ.get("SHELL")
    if env_shell and (shutil.which(env_shell) or os.path.isfile(env_shell)):
        return env_shell

    for candidate in _CANDIDATE_SHELLS:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


class LinuxTerminalAdapter(LocalProcessAdapter):
    name = "linux"

    def __init__(self, *, shell_path: str | None = None) -> None:
        self._configured_shell_path = shell_path

    def resolve_shell(self) -> str | None:
        return resolve_linux_shell(self._configured_shell_path)

    def get_capabilities(self) -> LinuxCapabilities:
        shell_path = self.resolve_shell()
        return LinuxCapabilities(
            platform="LINUX",
            shell=shell_path or "UNAVAILABLE",
            shell_available=shell_path is not None,
            supports_streaming=True,
            supports_cancellation=True,
            supports_timeout=True,
        )

    async def run(
        self,
        command: CommandSpec,
        *,
        audit: AuditSink | None = None,
        context: dict | None = None,
    ) -> ExecutionResult:
        ctx = context or {}
        self._emit(audit, LINUX_COMMAND_STARTED, ctx)

        try:
            result = await super().run(command, audit=audit, context=context)
        except asyncio.CancelledError:
            self._emit(audit, LINUX_COMMAND_CANCELLED, ctx)
            raise

        if result.timed_out:
            self._emit(audit, LINUX_COMMAND_TIMEOUT, ctx, exit_code=result.exit_code)
        elif result.status == ExecutionStatus.SUCCEEDED:
            self._emit(
                audit,
                LINUX_COMMAND_COMPLETED,
                ctx,
                exit_code=result.exit_code,
                stdout_preview=truncate_for_log(result.stdout),
            )
        else:
            self._emit(
                audit,
                LINUX_COMMAND_FAILED,
                ctx,
                exit_code=result.exit_code,
                stderr_preview=truncate_for_log(result.stderr),
            )

        return result

    def _process_creation_kwargs(self) -> dict:
        # Starts the child in its own session/process group (POSIX only) so
        # `_terminate` can signal the whole group — e.g. a shell command
        # that spawned children — without ever touching this process's own
        # group. `preexec_fn`/`start_new_session` are ignored on Windows;
        # this adapter never runs there.
        if hasattr(os, "setsid"):
            return {"start_new_session": True}
        return {}

    async def _terminate(self, process: asyncio.subprocess.Process) -> None:
        if hasattr(os, "killpg") and hasattr(os, "setsid") and process.returncode is None:
            try:
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                    return
                except TimeoutError:
                    os.killpg(pgid, signal.SIGKILL)
                    await process.wait()
                    return
            except (ProcessLookupError, PermissionError, OSError):
                pass  # fall through to the base kill as a last resort
        await super()._terminate(process)

    @staticmethod
    def _emit(audit: AuditSink | None, event_type: str, ctx: dict, **data: object) -> None:
        if audit is None:
            return
        audit.emit(
            AuditEvent(
                event_type=event_type,
                session_id=ctx.get("session_id"),
                command_id=ctx.get("command_id"),
                task_id=ctx.get("task_id"),
                data=data,
            )
        )


# Backward-compatible alias — Phase 5's platform_select.py / any external
# reference to the original class name keeps working.
LinuxAdapter = LinuxTerminalAdapter
