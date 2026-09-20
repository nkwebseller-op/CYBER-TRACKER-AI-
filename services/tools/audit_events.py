"""Audit event type names for Tool Discovery & the Trusted Tool Registry —
same `services.terminal.audit.AuditEvent`/`AuditSink` machinery used by
every other subsystem. Never carries an API key, a credential, or a
fabricated verification result."""

TOOL_DISCOVERED = "tool.discovered"
TOOL_METADATA_COLLECTED = "tool.metadata_collected"
TOOL_VERIFICATION_STARTED = "tool.verification.started"
TOOL_VERIFICATION_COMPLETED = "tool.verification.completed"
TOOL_VERIFICATION_FAILED = "tool.verification.failed"
TOOL_APPROVED = "tool.approved"
TOOL_BLOCKED = "tool.blocked"
TOOL_DEPRECATED = "tool.deprecated"
