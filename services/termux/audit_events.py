"""Audit event type names for the Termux connector — same shape and same
`services.terminal.audit.AuditEvent`/`AuditSink` machinery used by every
other terminal subsystem. Never carries a pairing code, a device token, or
raw command output beyond the same truncated preview convention used
elsewhere (see services.terminal.audit.truncate_for_log)."""

DEVICE_REGISTERED = "termux.device.registered"
DEVICE_PAIRED = "termux.device.paired"
DEVICE_AUTH_FAILED = "termux.device.authentication_failed"
DEVICE_REVOKED = "termux.device.revoked"
DEVICE_CONNECTED = "termux.device.connected"
DEVICE_DISCONNECTED = "termux.device.disconnected"

COMMAND_FORWARDED = "termux.command.forwarded"
COMMAND_COMPLETED = "termux.command.completed"
COMMAND_FAILED = "termux.command.failed"
COMMAND_TIMEOUT = "termux.command.timeout"
COMMAND_CANCELLED = "termux.command.cancelled"
CONNECTION_LOST = "termux.connection.lost"
MALFORMED_MESSAGE = "termux.message.malformed"
