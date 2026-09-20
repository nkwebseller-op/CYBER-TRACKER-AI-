"""Error classification for the self-healing pipeline (see
docs/ARCHITECTURE.md > Self-healing pipeline).

Phase 1 ships the taxonomy and a rule-based classifier over
`ExecutionResult`. It does not yet produce or apply fixes — a
`RecoveryAction` it proposes would have to pass through the same
PolicyEngine as any other action, and until services/tools defines real,
reviewed remediation actions there is nothing safe to register. Wiring
"propose fix" -> "apply fix" without that would itself be a form of
unreviewed autonomous execution, which this architecture explicitly
forbids.
"""

from dataclasses import dataclass
from enum import StrEnum

from services.terminal.adapters.base import ExecutionResult


class ErrorClass(StrEnum):
    MISSING_DEPENDENCY = "missing_dependency"
    WRONG_VERSION = "wrong_version"
    MISSING_EXECUTABLE = "missing_executable"
    PERMISSION_DENIED = "permission_denied"
    PLATFORM_MISMATCH = "platform_mismatch"
    INSTALL_FAILURE = "install_failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedError:
    error_class: ErrorClass
    confidence: float
    evidence: str


_SIGNATURES: list[tuple[ErrorClass, tuple[str, ...]]] = [
    (
        ErrorClass.MISSING_EXECUTABLE,
        ("command not found", "no such file or directory", "not recognized as"),
    ),
    (ErrorClass.PERMISSION_DENIED, ("permission denied", "access is denied")),
    (
        ErrorClass.MISSING_DEPENDENCY,
        ("modulenotfounderror", "no module named", "cannot find package"),
    ),
    (ErrorClass.TIMEOUT, ("execution timed out",)),
]


def classify(result: ExecutionResult) -> ClassifiedError:
    haystack = f"{result.stderr or ''}\n{result.stdout or ''}".lower()

    for error_class, needles in _SIGNATURES:
        for needle in needles:
            if needle in haystack:
                return ClassifiedError(error_class=error_class, confidence=0.7, evidence=needle)

    return ClassifiedError(error_class=ErrorClass.UNKNOWN, confidence=0.0, evidence="")
