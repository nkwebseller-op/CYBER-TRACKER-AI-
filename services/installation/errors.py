"""Structured error hierarchy for Tool Installation — same pattern as
services/terminal/errors.py, services/termux/errors.py, services/tools/errors.py."""

from enum import StrEnum


class InstallationErrorCode(StrEnum):
    TOOL_NOT_APPROVED = "tool_not_approved"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    PACKAGE_MANAGER_UNAVAILABLE = "package_manager_unavailable"
    DEPENDENCY_UNRESOLVED = "dependency_unresolved"
    POLICY_DENIED = "policy_denied"
    APPROVAL_REQUIRED = "approval_required"
    INSTALLATION_NOT_FOUND = "installation_not_found"
    INVALID_STATE_TRANSITION = "invalid_state_transition"
    RETRY_LIMIT_EXCEEDED = "retry_limit_exceeded"
    VERIFICATION_FAILED = "verification_failed"


class InstallationError(RuntimeError):
    def __init__(self, code: InstallationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ToolNotApprovedError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.TOOL_NOT_APPROVED, message)


class UnsupportedPlatformForToolError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.UNSUPPORTED_PLATFORM, message)


class PackageManagerUnavailableError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.PACKAGE_MANAGER_UNAVAILABLE, message)


class PolicyDeniedInstallError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.POLICY_DENIED, message)


class ApprovalRequiredError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.APPROVAL_REQUIRED, message)


class InstallationNotFoundError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.INSTALLATION_NOT_FOUND, message)


class InvalidStateTransitionError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.INVALID_STATE_TRANSITION, message)


class RetryLimitExceededError(InstallationError):
    def __init__(self, message: str) -> None:
        super().__init__(InstallationErrorCode.RETRY_LIMIT_EXCEEDED, message)
