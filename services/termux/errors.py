"""Structured error hierarchy for the Termux connector — same pattern as
services/terminal/errors.py. Every error carries a stable `code` and a
message safe to show a user or put in a log line, never a raw stack trace,
a token, or an internal transport detail.
"""

from enum import StrEnum


class TermuxErrorCode(StrEnum):
    DEVICE_NOT_REGISTERED = "device_not_registered"
    PAIRING_REQUIRED = "pairing_required"
    PAIRING_CODE_INVALID = "pairing_code_invalid"
    PAIRING_CODE_EXPIRED = "pairing_code_expired"
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_DENIED = "authorization_denied"
    DEVICE_OFFLINE = "device_offline"
    CONNECTOR_UNAVAILABLE = "connector_unavailable"
    TERMUX_UNAVAILABLE = "termux_unavailable"
    PERMISSION_UNAVAILABLE = "permission_unavailable"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    MALFORMED_REQUEST = "malformed_request"
    CONNECTION_LOST = "connection_lost"
    REVOKED_DEVICE = "revoked_device"


class TermuxConnectorError(RuntimeError):
    def __init__(self, code: TermuxErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class DeviceNotRegisteredError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.DEVICE_NOT_REGISTERED, message)


class PairingRequiredError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.PAIRING_REQUIRED, message)


class PairingCodeInvalidError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.PAIRING_CODE_INVALID, message)


class PairingCodeExpiredError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.PAIRING_CODE_EXPIRED, message)


class AuthenticationFailedError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.AUTHENTICATION_FAILED, message)


class DeviceOfflineError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.DEVICE_OFFLINE, message)


class RevokedDeviceError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.REVOKED_DEVICE, message)


class MalformedMessageError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.MALFORMED_REQUEST, message)


class CapabilityUnavailableError(TermuxConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(TermuxErrorCode.CAPABILITY_UNAVAILABLE, message)
