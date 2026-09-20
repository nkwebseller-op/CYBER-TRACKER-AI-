"""Common terminal adapter contract.

`CommandSpec.argv` is always a list of discrete arguments — never a shell
string. Adapters must invoke subprocesses via argv execution
(`asyncio.create_subprocess_exec`), never `shell=True`, so there is no
command-injection surface between a structured action and the OS.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


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


@dataclass
class ExecutionResult:
    adapter: str
    status: ExecutionStatus
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class TerminalAdapter(ABC):
    name: str

    @abstractmethod
    async def run(self, command: CommandSpec) -> ExecutionResult:
        """Execute the command and return its result. Must never invoke a
        shell; argv is executed directly."""
