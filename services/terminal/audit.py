"""Structured audit events for the Terminal Engine lifecycle.

Every meaningful state transition emits one of these events. The default
sink logs via structlog (never a secret, never full command output —
output is length-capped before it's included). A later phase can add a
sink that also writes to the AuditLogEntry table (apps/api/app/db/models.py)
or forwards to the WebSocket gateway for live streaming — this module
only defines the event shape and a pluggable `AuditSink` so the engine
itself never depends on a database or a transport.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

import structlog

_LOG_CONTENT_PREVIEW_CHARS = 200

# Event type names. Not an exhaustive enum on purpose — new event types can
# be introduced without touching this module — but these are the ones the
# engine itself emits.
SESSION_CREATED = "terminal.session.created"
SESSION_CLOSED = "terminal.session.closed"
SESSION_EXPIRED = "terminal.session.expired"
COMMAND_REQUESTED = "terminal.command.requested"
COMMAND_APPROVED = "terminal.command.approved"
COMMAND_REJECTED = "terminal.command.rejected"
COMMAND_STARTED = "terminal.command.started"
COMMAND_OUTPUT = "terminal.command.output"
COMMAND_COMPLETED = "terminal.command.completed"
COMMAND_FAILED = "terminal.command.failed"
COMMAND_TIMEOUT = "terminal.command.timeout"
COMMAND_CANCELLED = "terminal.command.cancelled"


@dataclass
class AuditEvent:
    event_type: str
    session_id: str | None
    command_id: str | None
    task_id: str | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    data: dict = field(default_factory=dict)


class AuditSink(Protocol):
    def emit(self, event: AuditEvent) -> None: ...


class LoggingAuditSink:
    """Default sink: structured logs only, never a database or a socket."""

    def __init__(self) -> None:
        self._logger = structlog.get_logger("terminal.audit")

    def emit(self, event: AuditEvent) -> None:
        self._logger.info(
            event.event_type,
            session_id=event.session_id,
            command_id=event.command_id,
            task_id=event.task_id,
            **event.data,
        )


def truncate_for_log(text: str | None, *, limit: int = _LOG_CONTENT_PREVIEW_CHARS) -> str | None:
    """Caps output before it goes anywhere near a log line — full output
    belongs in the command result, not in the audit trail."""
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [{len(text) - limit} more characters omitted]"
