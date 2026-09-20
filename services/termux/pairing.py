"""Device registration and pairing.

Authentication approach (documented per the phase requirement): this
project has no existing device-credential system to integrate with (the
only prior "auth" surface is `Settings.api_secret_key`, which authenticates
the API deployment itself, not an individual client) — so pairing uses a
minimal, well-understood two-step bearer-credential flow rather than a new
cryptographic protocol:

1. `register_device` creates a device record in PAIRING_REQUIRED and
   returns a short-lived, single-use, high-entropy pairing code
   (`secrets.token_urlsafe`) out of band (shown to the operator, entered
   into the Termux connector app). Only its SHA-256 hash is stored.
2. `confirm_pairing` — called by the connector app once the operator has
   entered the code — exchanges that code for a long-lived device token
   (also `secrets.token_urlsafe`, also stored only as a hash). The device
   moves to AUTHORIZED. The raw token is returned exactly once, in this
   response; it is never logged, never stored raw, and never returned
   again — losing it means re-pairing (`revoke_device` + `register_device`).
3. Every reconnect calls `authenticate(device_id, device_token)`, which
   compares the presented token's hash against the stored hash with
   `hmac.compare_digest` (constant-time; no early-exit string comparison).

This is deliberately not a bespoke crypto protocol: it's the same
"opaque bearer token, hashed at rest, compared in constant time" shape
already used for API keys/session tokens across the industry, applied to a
device instead of a user. Revocation is immediate and simply invalidates
the stored hash — no token rotation or expiry math needed for that path.
Transport security (TLS) is the API server's job, not this module's — see
services/termux/connection_manager.py's module docstring for the
production/dev-mode split.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from services.terminal.audit import AuditEvent, AuditSink, LoggingAuditSink
from services.termux.audit_events import (
    DEVICE_AUTH_FAILED,
    DEVICE_PAIRED,
    DEVICE_REGISTERED,
    DEVICE_REVOKED,
)
from services.termux.errors import (
    AuthenticationFailedError,
    DeviceNotRegisteredError,
    PairingCodeExpiredError,
    PairingCodeInvalidError,
    RevokedDeviceError,
)
from services.termux.models import DeviceState, TermuxCapability, TermuxDevice

_PAIRING_CODE_BYTES = 6  # ~48 bits of entropy, single-use, short TTL
_DEVICE_TOKEN_BYTES = 32


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class _PendingPairing:
    code_hash: str
    expires_at: datetime


class PairingService:
    def __init__(
        self,
        *,
        pairing_code_ttl_seconds: int = 300,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._pairing_code_ttl_seconds = pairing_code_ttl_seconds
        self._audit = audit_sink or LoggingAuditSink()
        self._devices: dict[UUID, TermuxDevice] = {}
        self._pending: dict[UUID, _PendingPairing] = {}
        self._token_hashes: dict[UUID, str] = {}

    def _emit(self, event_type: str, device: TermuxDevice, **data: object) -> None:
        self._audit.emit(
            AuditEvent(
                event_type=event_type,
                session_id=None,
                command_id=None,
                task_id=None,
                data={"device_id": str(device.id), "state": device.state.value, **data},
            )
        )

    def register_device(
        self,
        *,
        name: str,
        connector_version: str | None = None,
        capabilities: frozenset[TermuxCapability] = frozenset(),
    ) -> tuple[TermuxDevice, str]:
        """Returns the device record and the raw, one-time pairing code —
        the only place that code ever leaves this service in plaintext."""
        device = TermuxDevice(
            name=name,
            connector_version=connector_version,
            capabilities=capabilities,
            state=DeviceState.PAIRING_REQUIRED,
        )
        self._devices[device.id] = device

        raw_code = secrets.token_urlsafe(_PAIRING_CODE_BYTES)
        self._pending[device.id] = _PendingPairing(
            code_hash=_hash(raw_code),
            expires_at=datetime.now(UTC) + timedelta(seconds=self._pairing_code_ttl_seconds),
        )
        self._emit(DEVICE_REGISTERED, device, name=name)
        return device, raw_code

    def confirm_pairing(self, device_id: UUID, pairing_code: str) -> tuple[TermuxDevice, str]:
        """Returns the device record and the raw, one-time device token."""
        device = self._require_device(device_id)
        pending = self._pending.get(device_id)
        if pending is None:
            raise PairingCodeInvalidError("No pairing is pending for this device.")
        if datetime.now(UTC) > pending.expires_at:
            del self._pending[device_id]
            raise PairingCodeExpiredError("The pairing code has expired; register again.")
        if not hmac.compare_digest(pending.code_hash, _hash(pairing_code)):
            raise PairingCodeInvalidError("The pairing code is incorrect.")

        del self._pending[device_id]  # single-use
        raw_token = secrets.token_urlsafe(_DEVICE_TOKEN_BYTES)
        self._token_hashes[device_id] = _hash(raw_token)
        device.state = DeviceState.AUTHORIZED
        device.touch()
        self._emit(DEVICE_PAIRED, device)
        return device, raw_token

    def authenticate(self, device_id: UUID, device_token: str) -> TermuxDevice:
        device = self._require_device(device_id)
        if device.state == DeviceState.REVOKED:
            raise RevokedDeviceError("This device's credentials have been revoked.")

        stored_hash = self._token_hashes.get(device_id)
        if stored_hash is None or not hmac.compare_digest(stored_hash, _hash(device_token)):
            self._emit(DEVICE_AUTH_FAILED, device)
            raise AuthenticationFailedError("Device authentication failed.")
        return device

    def revoke_device(self, device_id: UUID) -> TermuxDevice:
        device = self._require_device(device_id)
        device.state = DeviceState.REVOKED
        device.revoked_at = datetime.now(UTC)
        self._token_hashes.pop(device_id, None)
        self._pending.pop(device_id, None)
        self._emit(DEVICE_REVOKED, device)
        return device

    def mark_connected(self, device_id: UUID) -> TermuxDevice:
        device = self._require_device(device_id)
        device.state = DeviceState.CONNECTED
        device.touch()
        return device

    def mark_disconnected(self, device_id: UUID) -> TermuxDevice:
        device = self._require_device(device_id)
        if device.state == DeviceState.CONNECTED:
            device.state = DeviceState.DISCONNECTED
        device.touch()
        return device

    @property
    def pairing_code_ttl_seconds(self) -> int:
        return self._pairing_code_ttl_seconds

    def get_device(self, device_id: UUID) -> TermuxDevice:
        return self._require_device(device_id)

    def list_devices(self) -> list[TermuxDevice]:
        return list(self._devices.values())

    def _require_device(self, device_id: UUID) -> TermuxDevice:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceNotRegisteredError(f"Device {device_id} is not registered.")
        return device
