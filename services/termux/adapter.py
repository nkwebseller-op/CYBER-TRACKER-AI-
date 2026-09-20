"""RemoteTermuxAdapter — the `TerminalAdapter` implementation for a
specific, already-paired Android/Termux device.

Unlike Windows/Linux/macOS (services/terminal/adapters/*.py), this adapter
never runs a local process: `run()` forwards the already-vetted
`CommandSpec` to `TermuxConnectionManager.execute()`, which sends it to the
device over its authenticated connection and waits for the result. This is
intentionally the *only* new thing here — everything upstream (session
lifecycle, policy gate, `ApprovedExecution`, timeout/output-limit
enforcement in `CommandSpec`) is the same `TerminalEngine` architecture
every other platform adapter uses. There is no second terminal pipeline.

One `RemoteTermuxAdapter` targets exactly one device — a
`TerminalEngine(adapter=RemoteTermuxAdapter(manager, device_id))` is scoped
to that device for its lifetime, the same way tests already construct
`TerminalEngine(adapter=WindowsTerminalAdapter())` for a specific platform.
"""

import asyncio
from uuid import UUID

from services.terminal.adapters.base import (
    CommandSpec,
    ExecutionResult,
    ExecutionStatus,
    TerminalAdapter,
)
from services.terminal.audit import AuditSink
from services.termux.connection_manager import TermuxConnectionManager
from services.termux.errors import TermuxConnectorError


class RemoteTermuxAdapter(TerminalAdapter):
    name = "termux"

    def __init__(self, connection_manager: TermuxConnectionManager, device_id: UUID) -> None:
        self._manager = connection_manager
        self._device_id = device_id

    async def run(
        self,
        command: CommandSpec,
        *,
        audit: AuditSink | None = None,
        context: dict | None = None,
    ) -> ExecutionResult:
        """`audit`/`context` are accepted for interface compatibility;
        TermuxConnectionManager emits its own `termux.*` events directly
        (it needs the device id, which isn't part of the generic
        session/command/task context every other adapter uses)."""
        try:
            return await self._manager.execute(self._device_id, command, context=context)
        except asyncio.CancelledError:
            raise
        except TermuxConnectorError as exc:
            # Connectivity/auth failures are reported the same structured
            # way a local adapter reports "process could not be created" —
            # never a raw exception or stack trace reaching the caller.
            return ExecutionResult(
                adapter=self.name,
                status=ExecutionStatus.FAILED,
                stderr=str(exc),
            )
