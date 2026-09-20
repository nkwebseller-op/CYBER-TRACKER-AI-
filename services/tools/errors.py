"""Structured error hierarchy for the Tool Registry — same pattern as
services/terminal/errors.py and services/termux/errors.py."""

from enum import StrEnum


class ToolRegistryErrorCode(StrEnum):
    TOOL_NOT_FOUND = "tool_not_found"
    DUPLICATE_TOOL = "duplicate_tool"
    INVALID_CANDIDATE = "invalid_candidate"
    VERIFICATION_FAILED = "verification_failed"
    SOURCE_UNTRUSTED = "source_untrusted"
    CAPABILITY_PROHIBITED = "capability_prohibited"
    INVALID_TRUST_TRANSITION = "invalid_trust_transition"


class ToolRegistryError(RuntimeError):
    def __init__(self, code: ToolRegistryErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ToolNotFoundError(ToolRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(ToolRegistryErrorCode.TOOL_NOT_FOUND, message)


class DuplicateToolError(ToolRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(ToolRegistryErrorCode.DUPLICATE_TOOL, message)


class InvalidCandidateError(ToolRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(ToolRegistryErrorCode.INVALID_CANDIDATE, message)


class CapabilityProhibitedError(ToolRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(ToolRegistryErrorCode.CAPABILITY_PROHIBITED, message)


class InvalidTrustTransitionError(ToolRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(ToolRegistryErrorCode.INVALID_TRUST_TRANSITION, message)
