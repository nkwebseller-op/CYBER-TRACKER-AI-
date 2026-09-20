"""Windows Terminal Adapter.

    TerminalEngine
          |
    WindowsTerminalAdapter (this file)
          |
    Controlled Windows process (argv exec, never shell=True)
          |
    stdout / stderr -> TerminalCommandResult

Inherits all process-control machinery (timeout, output caps, env
allowlisting, cancellation-safe kill) from LocalProcessAdapter — the same
base every other adapter uses — and adds three Windows-specific things:

1. PowerShell resolution/availability (`resolve_shell` / `get_capabilities`),
   preferring `pwsh` (PowerShell 7+) over legacy `powershell.exe`.
2. `build_powershell_command`, the *only* sanctioned way to wrap a script
   for PowerShell execution — it takes an already-vetted script string
   (never user- or AI-supplied text; see
   services/terminal/command_templates.py) and returns argv, never a
   shell string.
3. Best-effort Windows process-tree termination (`taskkill /T /F`) on
   timeout/cancellation/output-limit-exceeded, falling back to the base
   class's plain `process.kill()` everywhere else (including this
   sandbox's non-Windows dev/test environment).

Nothing here decides whether a command is authorized — see
services/terminal/engine.py, which only ever calls `run()` after
`ApprovedExecution.from_policy_decision` has succeeded.
"""

import asyncio
import os
import shutil
from dataclasses import dataclass

from services.terminal.adapters.base import CommandSpec, ExecutionResult, ExecutionStatus
from services.terminal.adapters.local_process import LocalProcessAdapter
from services.terminal.audit import AuditEvent, AuditSink, truncate_for_log

WINDOWS_COMMAND_STARTED = "windows.command.started"
WINDOWS_COMMAND_COMPLETED = "windows.command.completed"
WINDOWS_COMMAND_FAILED = "windows.command.failed"
WINDOWS_COMMAND_TIMEOUT = "windows.command.timeout"
WINDOWS_COMMAND_CANCELLED = "windows.command.cancelled"
WINDOWS_SESSION_CREATED = "windows.session.created"


@dataclass(frozen=True)
class WindowsCapabilities:
    """Reflects what this runtime can *actually* do — never hardcoded.
    `shell`/`shell_available` are computed by probing for a real
    executable at the moment of the call."""

    platform: str
    shell: str
    shell_available: bool
    supports_streaming: bool
    supports_cancellation: bool
    supports_timeout: bool


def resolve_powershell_executable(preferred_path: str | None = None) -> str | None:
    """Prefers a configured path, then `pwsh` (PowerShell 7+, cross-arch
    and the modern recommendation), then legacy `powershell.exe`."""
    if preferred_path:
        resolved = shutil.which(preferred_path)
        if resolved:
            return resolved
        if os.path.isfile(preferred_path):
            return preferred_path
        return None  # an explicitly configured path that doesn't exist is not silently ignored
    return shutil.which("pwsh") or shutil.which("powershell.exe") or shutil.which("powershell")


class WindowsTerminalAdapter(LocalProcessAdapter):
    name = "windows"

    def __init__(self, *, powershell_path: str | None = None) -> None:
        self._configured_powershell_path = powershell_path

    def resolve_shell(self) -> str | None:
        return resolve_powershell_executable(self._configured_powershell_path)

    def get_capabilities(self) -> WindowsCapabilities:
        shell_path = self.resolve_shell()
        return WindowsCapabilities(
            platform="WINDOWS",
            shell="POWERSHELL" if shell_path else "UNAVAILABLE",
            shell_available=shell_path is not None,
            supports_streaming=True,
            supports_cancellation=True,
            supports_timeout=True,
        )

    @staticmethod
    def build_powershell_command(script: str, *, powershell_path: str) -> list[str]:
        """Wraps an already-vetted script string as argv for controlled
        PowerShell execution — never built from raw user/AI text. The
        caller (a command template, never the engine or the AI) owns the
        script content; this only owns safe invocation flags."""
        return [
            powershell_path,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ]

    async def _terminate(self, process: asyncio.subprocess.Process) -> None:
        if os.name == "nt" and process.returncode is None:
            try:
                killer = await asyncio.create_subprocess_exec(
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await killer.wait()
            except (FileNotFoundError, ProcessLookupError, OSError):
                pass  # fall through to the base kill as a last resort
        await super()._terminate(process)

    async def run(
        self,
        command: CommandSpec,
        *,
        audit: AuditSink | None = None,
        context: dict | None = None,
    ) -> ExecutionResult:
        ctx = context or {}
        self._emit(audit, WINDOWS_COMMAND_STARTED, ctx)

        try:
            result = await super().run(command, audit=audit, context=context)
        except asyncio.CancelledError:
            self._emit(audit, WINDOWS_COMMAND_CANCELLED, ctx)
            raise

        if result.timed_out:
            self._emit(audit, WINDOWS_COMMAND_TIMEOUT, ctx, exit_code=result.exit_code)
        elif result.status == ExecutionStatus.SUCCEEDED:
            self._emit(
                audit,
                WINDOWS_COMMAND_COMPLETED,
                ctx,
                exit_code=result.exit_code,
                stdout_preview=truncate_for_log(result.stdout),
            )
        else:
            self._emit(
                audit,
                WINDOWS_COMMAND_FAILED,
                ctx,
                exit_code=result.exit_code,
                stderr_preview=truncate_for_log(result.stderr),
            )

        return result

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
WindowsAdapter = WindowsTerminalAdapter
