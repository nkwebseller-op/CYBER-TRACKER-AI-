"""Structured error hierarchy for the Terminal Engine.

Every error carries a stable `code` and a message safe to show a user or
put in a log line — never a raw stack trace, a secret, or an internal
path. Callers (the API layer) map `code` to an HTTP status; nothing here
assumes a transport.
"""

from enum import StrEnum


class TerminalErrorCode(StrEnum):
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    INVALID_REQUEST = "invalid_request"
    INVALID_WORKING_DIRECTORY = "invalid_working_directory"
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_EXPIRED = "session_expired"
    SESSION_NOT_READY = "session_not_ready"
    AUTHORIZATION_REJECTED = "authorization_rejected"
    PROCESS_CREATION_FAILED = "process_creation_failed"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    TERMINATION_FAILED = "termination_failed"
    OUTPUT_LIMIT_EXCEEDED = "output_limit_exceeded"


class TerminalEngineError(RuntimeError):
    def __init__(self, code: TerminalErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class UnsupportedPlatformError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.UNSUPPORTED_PLATFORM, message)


class InvalidRequestError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.INVALID_REQUEST, message)


class InvalidWorkingDirectoryError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.INVALID_WORKING_DIRECTORY, message)


class SessionNotFoundError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.SESSION_NOT_FOUND, message)


class SessionExpiredError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.SESSION_EXPIRED, message)


class SessionNotReadyError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.SESSION_NOT_READY, message)


class AuthorizationRejectedError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.AUTHORIZATION_REJECTED, message)


class ProcessCreationError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.PROCESS_CREATION_FAILED, message)


class TerminationFailedError(TerminalEngineError):
    def __init__(self, message: str) -> None:
        super().__init__(TerminalErrorCode.TERMINATION_FAILED, message)
