import sys

from services.terminal.audit import AuditEvent, AuditSink


def python_command(code: str) -> list[str]:
    """A harmless, cross-platform test command: the running interpreter
    itself. Never a destructive or platform-specific shell command."""
    return [sys.executable, "-c", code]


class RecordingAuditSink(AuditSink):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    @property
    def event_types(self) -> list[str]:
        return [event.event_type for event in self.events]
