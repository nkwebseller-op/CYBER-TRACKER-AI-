"""Shared implementation for adapters that run commands as local OS
processes (Linux, macOS, Termux). Windows subclasses this too since
asyncio's subprocess API is cross-platform; only shell/tooling
peculiarities differ per adapter subclass.

Phase 5: output is read incrementally (not buffered all at once via
`communicate()`) so a configured `max_stdout_bytes`/`max_stderr_bytes` cap
bounds memory regardless of how much a command actually writes — excess
bytes are discarded, not stored, and the process is killed once a cap is
exceeded rather than left to keep producing output nobody will see.
"""

import asyncio
import os
from datetime import UTC, datetime

from services.terminal.adapters.base import (
    CommandSpec,
    ExecutionResult,
    ExecutionStatus,
    TerminalAdapter,
)

_READ_CHUNK_SIZE = 65536


class _CappedReader:
    """Reads a stream until EOF, keeping at most `max_bytes` of it and
    signaling the caller (via `exceeded`) the moment the cap is passed so
    the process can be killed instead of left running to no purpose."""

    def __init__(self, stream: asyncio.StreamReader | None, max_bytes: int | None) -> None:
        self._stream = stream
        self._max_bytes = max_bytes
        self._chunks: list[bytes] = []
        self._total = 0
        self.exceeded = False

    async def read_all(self) -> None:
        if self._stream is None:
            return
        while True:
            chunk = await self._stream.read(_READ_CHUNK_SIZE)
            if not chunk:
                return
            if self._max_bytes is None:
                self._chunks.append(chunk)
                self._total += len(chunk)
                continue

            remaining = self._max_bytes - self._total
            if remaining <= 0:
                self.exceeded = True
                continue  # keep draining so the process's pipe never fills and blocks it
            if len(chunk) > remaining:
                self._chunks.append(chunk[:remaining])
                self._total += remaining
                self.exceeded = True
            else:
                self._chunks.append(chunk)
                self._total += len(chunk)

    @property
    def text(self) -> str:
        return b"".join(self._chunks).decode(errors="replace")


def _filtered_env(command: CommandSpec) -> dict[str, str]:
    if command.env_allowlist is None:
        base = dict(os.environ)
    else:
        base = {key: os.environ[key] for key in command.env_allowlist if key in os.environ}
    base.update(command.env_overrides)
    return base


class LocalProcessAdapter(TerminalAdapter):
    async def run(self, command: CommandSpec) -> ExecutionResult:
        started_at = datetime.now(UTC)
        env = _filtered_env(command)

        try:
            process = await asyncio.create_subprocess_exec(
                *command.argv,
                cwd=command.working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            return ExecutionResult(
                adapter=self.name,
                status=ExecutionStatus.FAILED,
                stderr=f"Executable not found: {exc}",
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        except PermissionError as exc:
            return ExecutionResult(
                adapter=self.name,
                status=ExecutionStatus.FAILED,
                stderr=f"Permission denied: {exc}",
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )

        stdout_reader = _CappedReader(process.stdout, command.max_stdout_bytes)
        stderr_reader = _CappedReader(process.stderr, command.max_stderr_bytes)

        async def drain_and_wait() -> None:
            await asyncio.gather(stdout_reader.read_all(), stderr_reader.read_all())
            if stdout_reader.exceeded or stderr_reader.exceeded:
                await _kill(process)
            await process.wait()

        try:
            await asyncio.wait_for(drain_and_wait(), timeout=command.timeout_seconds)
        except TimeoutError:
            await _kill(process)
            return ExecutionResult(
                adapter=self.name,
                status=ExecutionStatus.FAILED,
                stdout=stdout_reader.text,
                stderr=stderr_reader.text,
                stdout_truncated=stdout_reader.exceeded,
                stderr_truncated=stderr_reader.exceeded,
                timed_out=True,
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )

        status = ExecutionStatus.SUCCEEDED if process.returncode == 0 else ExecutionStatus.FAILED
        return ExecutionResult(
            adapter=self.name,
            status=status,
            exit_code=process.returncode,
            stdout=stdout_reader.text,
            stderr=stderr_reader.text,
            stdout_truncated=stdout_reader.exceeded,
            stderr_truncated=stderr_reader.exceeded,
            started_at=started_at,
            finished_at=datetime.now(UTC),
        )


async def _kill(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        process.kill()
        await process.wait()
    except ProcessLookupError:
        pass  # already exited between the check and the kill
