"""Core data models for the Termux connector: device identity, connection
state machine, and declared capabilities. Nothing here ever holds a raw
pairing code or device token — see services/termux/pairing.py, which only
ever stores salted hashes.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class DeviceState(StrEnum):
    UNREGISTERED = "UNREGISTERED"
    PAIRING_REQUIRED = "PAIRING_REQUIRED"
    PAIRING = "PAIRING"
    AUTHORIZED = "AUTHORIZED"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    REVOKED = "REVOKED"


# Declared, not assumed: a device only gets a capability listed here once
# its connector app reports implementing it. Listing a capability is
# informational only — it never grants permission to use it; the policy
# engine and command-template registry are the only source of authorization
# (see services/termux/connection_manager.py, which checks both instead of
# trusting the device's own capability claims).
class TermuxCapability(StrEnum):
    TERMINAL_EXECUTION = "terminal_execution"
    FILESYSTEM_ACCESS = "filesystem_access"
    NETWORK_TOOLS = "network_tools"
    PACKAGE_MANAGER = "package_manager"
    BLUETOOTH_INTERFACE = "bluetooth_interface"


_ACTIVE_STATES = frozenset(
    {DeviceState.AUTHORIZED, DeviceState.CONNECTED, DeviceState.DISCONNECTED,
     DeviceState.RECONNECTING}
)


@dataclass
class TermuxDevice:
    """A registered Android/Termux device. `platform` is always the string
    form of PlatformIdentifier.ANDROID_TERMUX — kept as a plain string here
    (rather than importing the enum) so this module has no dependency on
    services.terminal, matching the existing services/ boundary style."""

    id: UUID = field(default_factory=uuid4)
    name: str = "unnamed-device"
    platform: str = "ANDROID_TERMUX"
    connector_version: str | None = None
    capabilities: frozenset[TermuxCapability] = field(default_factory=frozenset)
    state: DeviceState = DeviceState.UNREGISTERED
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None

    def touch(self) -> None:
        self.last_seen_at = datetime.now(UTC)

    def is_active_credential(self) -> bool:
        return self.state in _ACTIVE_STATES

    def to_public_dict(self) -> dict:
        """Never includes a token, a pairing code, or any raw Android
        device data — only the fields an authorized operator's UI needs to
        show connection/authorization state."""
        return {
            "id": str(self.id),
            "name": self.name,
            "platform": self.platform,
            "connectorVersion": self.connector_version,
            "capabilities": sorted(c.value for c in self.capabilities),
            "state": self.state.value,
            "registeredAt": self.registered_at.isoformat(),
            "lastSeenAt": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "revokedAt": self.revoked_at.isoformat() if self.revoked_at else None,
        }
