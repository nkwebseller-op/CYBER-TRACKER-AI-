"""Common terminal adapter contract.

`CommandSpec.argv` is always a list of discrete arguments — never a shell
string. Adapters must invoke subprocesses via argv execution
(`asyncio.create_subprocess_exec`), never `shell=True`, so there is no
command-injection surface between a structured action and the OS.

Phase 5 additions: `env_allowlist` (only inherit named host environment
variables instead of the full, potentially secret-laden, process
environment) and output size caps, so the Terminal Engine can enforce
"never expose secrets to command output" and "prevent uncontrolled output
growth" at the one place every adapter shares.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from services.terminal.audit import AuditSink


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RECOVERING = "recovering"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class CommandSpec:
    argv: list[str]
    timeout_seconds: int = 60
    working_dir: str | None = None
    env_overrides: dict[str, str] = field(default_factory=dict)
    # None preserves the pre-Phase-5 default (inherit the full host
    # environment) for any existing caller that doesn't pass this.
    # Terminal Engine callers always pass an explicit allowlist.
    env_allowlist: tuple[str, ...] | None = None
    # None means "no cap" (pre-Phase-5 behavior). The Terminal Engine
    # always sets these from services.terminal.config.
    max_stdout_bytes: int | None = None
    max_stderr_bytes: int | None = None


@dataclass
class ExecutionResult:
    adapter: str
    status: ExecutionStatus
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    timed_out: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class TerminalAdapter(ABC):
    name: str

    @abstractmethod
    async def run(
        self,
        command: CommandSpec,
        *,
        audit: AuditSink | None = None,
        context: dict | None = None,
    ) -> ExecutionResult:
        """Execute the command and return its result. Must never invoke a
        shell; argv is executed directly. `audit`/`context` (session/
        command/task ids) are optional — a subclass may use them to emit
        its own platform-specific audit events (see
        services/terminal/adapters/windows.py); the base implementation
        ignores them."""
