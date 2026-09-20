"""Termux connection manager: the transport-independent half of the remote
connector.

    Android device (Termux connector app)
          |  authenticated transport (see module docstring below)
    TermuxConnectionManager (this file)
          |
    RemoteTermuxAdapter (services/termux/adapter.py)
          |
    TerminalEngine                        (unchanged from Phase 5)

This module never imports FastAPI or any web framework — it depends only
on a minimal `TermuxTransport` protocol (anything with an async
`send_json`), so the real WebSocket wiring (apps/api/app/ws/termux_gateway.py)
is a thin adapter around this, and tests can drive it with a plain fake.

Transport security: production deployments terminate TLS at the ASGI
server/reverse proxy in front of this API (the same as every other route
here) — `wss://` for the device connection, exactly like `https://` for
the REST pairing endpoints. This module does not, and must not, weaken
that; it has no "insecure mode" flag. Local development against a
non-TLS `ws://localhost` is not a special code path here — it's simply
what pointing the connector app at `http://localhost:8000` naturally
gives you, isolated from production by environment, not by weakened code.

Authorization boundary: `execute()` takes a `CommandSpec` that the caller
(services/terminal/engine.py, via RemoteTermuxAdapter) has already built
from a `TerminalCommandRequest` whose `authorization_context` was ALLOWed
or explicitly approved. This manager has no independent authorization
logic of its own — it only checks that the *device* itself is connected,
authenticated, and not revoked, which is a connectivity precondition, not
an authorization decision.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from services.terminal.adapters.base import CommandSpec, ExecutionResult, ExecutionStatus
from services.terminal.audit import AuditEvent, AuditSink, LoggingAuditSink, truncate_for_log
from services.termux.audit_events import (
    COMMAND_CANCELLED,
    COMMAND_COMPLETED,
    COMMAND_FAILED,
    COMMAND_FORWARDED,
    COMMAND_TIMEOUT,
    CONNECTION_LOST,
    DEVICE_CONNECTED,
    DEVICE_DISCONNECTED,
    MALFORMED_MESSAGE,
)
from services.termux.errors import DeviceOfflineError, MalformedMessageError
from services.termux.pairing import PairingService


class TermuxTransport(Protocol):
    async def send_json(self, message: dict) -> None: ...


@dataclass
class _PendingCommand:
    device_id: UUID
    future: "asyncio.Future[ExecutionResult]"
    max_stdout_bytes: int | None
    max_stderr_bytes: int | None
    stdout_chunks: list[str] = field(default_factory=list)
    stderr_chunks: list[str] = field(default_factory=list)
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def append(self, kind: str, text: str) -> None:
        if kind == "stdout":
            chunks, cap = self.stdout_chunks, self.max_stdout_bytes
        else:
            chunks, cap = self.stderr_chunks, self.max_stderr_bytes
        if cap is not None:
            used = self.stdout_bytes if kind == "stdout" else self.stderr_bytes
            remaining = cap - used
            if remaining <= 0:
                if kind == "stdout":
                    self.stdout_truncated = True
                else:
                    self.stderr_truncated = True
                return
            if len(text.encode()) > remaining:
                text = text.encode()[:remaining].decode(errors="replace")
                if kind == "stdout":
                    self.stdout_truncated = True
                else:
                    self.stderr_truncated = True
        chunks.append(text)
        added = len(text.encode())
        if kind == "stdout":
            self.stdout_bytes += added
        else:
            self.stderr_bytes += added


class TermuxConnectionManager:
    def __init__(
        self,
        pairing: PairingService,
        *,
        audit_sink: AuditSink | None = None,
        cancel_grace_seconds: float = 2.0,
    ) -> None:
        self._pairing = pairing
        self._audit = audit_sink or LoggingAuditSink()
        self._transports: dict[UUID, TermuxTransport] = {}
        self._pending: dict[UUID, _PendingCommand] = {}
        self._cancel_grace_seconds = cancel_grace_seconds

    def _emit(self, event_type: str, *, device_id: UUID, command_id: UUID | None = None,
              **data: object) -> None:
        self._audit.emit(
            AuditEvent(
                event_type=event_type,
                session_id=None,
                command_id=str(command_id) if command_id else None,
                task_id=None,
                data={"device_id": str(device_id), **data},
            )
        )

    # --- connection lifecycle ------------------------------------------------

    async def handle_connect(
        self, device_id: UUID, device_token: str, transport: TermuxTransport
    ) -> None:
        """Raises AuthenticationFailedError / RevokedDeviceError /
        DeviceNotRegisteredError (all from services.termux.errors) without
        ever storing the transport — a failed auth never becomes a
        connected device."""
        self._pairing.authenticate(device_id, device_token)
        self._transports[device_id] = transport
        self._pairing.mark_connected(device_id)
        self._emit(DEVICE_CONNECTED, device_id=device_id)

    def handle_disconnect(self, device_id: UUID) -> None:
        self._transports.pop(device_id, None)
        self._pairing.mark_disconnected(device_id)
        self._emit(DEVICE_DISCONNECTED, device_id=device_id)

        lost = [cid for cid, cmd in self._pending.items() if cmd.device_id == device_id]
        for command_id in lost:
            pending = self._pending.pop(command_id)
            if not pending.future.done():
                pending.future.set_result(
                    ExecutionResult(
                        adapter="termux",
                        status=ExecutionStatus.FAILED,
                        stderr="Connection to the device was lost mid-command.",
                        started_at=pending.started_at,
                        finished_at=datetime.now(UTC),
                    )
                )
            self._emit(CONNECTION_LOST, device_id=device_id, command_id=command_id)

    def is_connected(self, device_id: UUID) -> bool:
        return device_id in self._transports

    # --- command execution -----------------------------------------------------

    async def execute(
        self, device_id: UUID, command: CommandSpec, *, context: dict | None = None
    ) -> ExecutionResult:
        transport = self._transports.get(device_id)
        if transport is None:
            raise DeviceOfflineError(f"Device {device_id} is not currently connected.")

        command_id = uuid4()
        loop = asyncio.get_running_loop()
        pending = _PendingCommand(
            device_id=device_id,
            future=loop.create_future(),
            max_stdout_bytes=command.max_stdout_bytes,
            max_stderr_bytes=command.max_stderr_bytes,
        )
        self._pending[command_id] = pending

        # The remote device gets an explicit envOverrides map and nothing
        # else — never the server's own host environment, which the device
        # has no business seeing regardless of env_allowlist (that setting
        # only ever applied to a *local* process's inherited environment).
        await transport.send_json(
            {
                "type": "command_request",
                "commandId": str(command_id),
                "argv": command.argv,
                "workingDirectory": command.working_dir,
                "timeoutSeconds": command.timeout_seconds,
                "envOverrides": command.env_overrides,
            }
        )
        self._emit(COMMAND_FORWARDED, device_id=device_id, command_id=command_id)

        try:
            result = await asyncio.wait_for(pending.future, timeout=command.timeout_seconds)
        except TimeoutError:
            self._pending.pop(command_id, None)
            await self._best_effort_cancel(transport, command_id)
            self._emit(COMMAND_TIMEOUT, device_id=device_id, command_id=command_id)
            return ExecutionResult(
                adapter="termux",
                status=ExecutionStatus.FAILED,
                stdout="".join(pending.stdout_chunks),
                stderr="".join(pending.stderr_chunks),
                stdout_truncated=pending.stdout_truncated,
                stderr_truncated=pending.stderr_truncated,
                timed_out=True,
                started_at=pending.started_at,
                finished_at=datetime.now(UTC),
            )
        except asyncio.CancelledError:
            self._pending.pop(command_id, None)
            await self._best_effort_cancel(transport, command_id)
            self._emit(COMMAND_CANCELLED, device_id=device_id, command_id=command_id)
            raise
        finally:
            self._pending.pop(command_id, None)

        if result.status == ExecutionStatus.SUCCEEDED:
            self._emit(
                COMMAND_COMPLETED,
                device_id=device_id,
                command_id=command_id,
                exit_code=result.exit_code,
                stdout_preview=truncate_for_log(result.stdout),
            )
        else:
            self._emit(
                COMMAND_FAILED,
                device_id=device_id,
                command_id=command_id,
                exit_code=result.exit_code,
                stderr_preview=truncate_for_log(result.stderr),
            )
        return result

    async def _best_effort_cancel(self, transport: TermuxTransport, command_id: UUID) -> None:
        try:
            await transport.send_json({"type": "command_cancel", "commandId": str(command_id)})
        except Exception:  # noqa: BLE001 - best-effort notification only
            pass

    # --- inbound message handling (called by the WebSocket gateway) -----------

    def handle_inbound_message(self, device_id: UUID, message: dict) -> None:
        """Dispatches one message from a connected device. Never raises for
        an unknown/stale command id (a late message after timeout/cancel is
        expected, not an error) — only genuinely malformed messages raise
        MalformedMessageError, which the caller logs and drops rather than
        letting take down the connection."""
        if not isinstance(message, dict) or "type" not in message:
            self._emit(MALFORMED_MESSAGE, device_id=device_id)
            raise MalformedMessageError("Message is missing a 'type' field.")

        message_type = message["type"]
        command_id_raw = message.get("commandId")
        if message_type in {"stdout", "stderr", "command_completed", "command_failed"} and (
            not command_id_raw
        ):
            self._emit(MALFORMED_MESSAGE, device_id=device_id)
            raise MalformedMessageError(f"Message of type '{message_type}' is missing commandId.")

        command_id = UUID(command_id_raw) if command_id_raw else None
        pending = self._pending.get(command_id) if command_id else None
        if pending is None or pending.device_id != device_id:
            return  # stale/unknown command id — not an error, just ignored

        if message_type == "stdout":
            pending.append("stdout", str(message.get("data", "")))
        elif message_type == "stderr":
            pending.append("stderr", str(message.get("data", "")))
        elif message_type == "command_completed":
            self._resolve(
                pending, ExecutionStatus.SUCCEEDED, exit_code=message.get("exitCode", 0)
            )
        elif message_type == "command_failed":
            self._resolve(
                pending,
                ExecutionStatus.FAILED,
                exit_code=message.get("exitCode"),
                extra_stderr=str(message.get("errorMessage", "")),
            )

    def _resolve(
        self,
        pending: _PendingCommand,
        status: ExecutionStatus,
        *,
        exit_code: int | None,
        extra_stderr: str = "",
    ) -> None:
        if pending.future.done():
            return
        stderr = "".join(pending.stderr_chunks) + extra_stderr
        pending.future.set_result(
            ExecutionResult(
                adapter="termux",
                status=status,
                exit_code=exit_code,
                stdout="".join(pending.stdout_chunks),
                stderr=stderr,
                stdout_truncated=pending.stdout_truncated,
                stderr_truncated=pending.stderr_truncated,
                started_at=pending.started_at,
                finished_at=datetime.now(UTC),
            )
        )
