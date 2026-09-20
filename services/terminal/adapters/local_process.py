"""Shared implementation for adapters that run commands as local OS
processes (Linux, macOS, Termux). Windows subclasses this too since
asyncio's subprocess API is cross-platform; only shell/tooling
peculiarities differ per adapter subclass."""

import asyncio
import os
from datetime import UTC, datetime

from services.terminal.adapters.base import (
    CommandSpec,
    ExecutionResult,
    ExecutionStatus,
    TerminalAdapter,
)


class LocalProcessAdapter(TerminalAdapter):
    async def run(self, command: CommandSpec) -> ExecutionResult:
        started_at = datetime.now(UTC)
        env = {**os.environ, **command.env_overrides}

        try:
            process = await asyncio.create_subprocess_exec(
                *command.argv,
                cwd=command.working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=command.timeout_seconds
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResult(
                    adapter=self.name,
                    status=ExecutionStatus.FAILED,
                    stderr="Execution timed out.",
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                )

            status = (
                ExecutionStatus.SUCCEEDED if process.returncode == 0 else ExecutionStatus.FAILED
            )
            return ExecutionResult(
                adapter=self.name,
                status=status,
                exit_code=process.returncode,
                stdout=stdout_bytes.decode(errors="replace"),
                stderr=stderr_bytes.decode(errors="replace"),
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        except FileNotFoundError as exc:
            return ExecutionResult(
                adapter=self.name,
                status=ExecutionStatus.FAILED,
                stderr=f"Executable not found: {exc}",
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
