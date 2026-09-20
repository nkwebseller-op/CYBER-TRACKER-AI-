"""Termux connector configuration — same plain-dataclass, decoupled-from-
apps/api pattern as services/terminal/config.py."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TermuxConnectorConfig:
    pairing_code_ttl_seconds: int = 300  # 5 minutes to enter the code
    max_registered_devices: int = 50
    # How long a best-effort "command_cancel" notification is allowed to
    # matter before the manager gives up waiting on it — the cancellation
    # itself (marking the result CANCELLED/TIMEOUT) never waits on the
    # device acknowledging.
    cancel_grace_seconds: float = 2.0
