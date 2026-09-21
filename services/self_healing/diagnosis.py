"""DiagnosisEngine: turns raw failure signals (stderr, exit code, timeout
flag, policy-denied flag) into a structured `Diagnosis` with confidence
and supporting evidence.

Deterministic — never asks the LLM to guess a root cause, so the same
signals always produce the same diagnosis. This complements (does not
replace) the simpler `services.agent_orchestrator.recovery.ErrorClassifier`;
the classifier picks a category, this engine explains WHY with cited
signals.
"""

import re
from dataclasses import dataclass

from services.self_healing.models import Diagnosis, DiagnosisConfidence


@dataclass(frozen=True)
class FailureSignals:
    stderr: str | None = None
    stdout: str | None = None
    exit_code: int | None = None
    timed_out: bool = False
    policy_denied: bool = False
    error_category: str | None = None  # from the upstream classifier, if any


# (regex, category, root_cause_template, confidence) — order-sensitive:
# more specific hints come first.
_DIAGNOSIS_HINTS: tuple[tuple[re.Pattern[str], str, str, DiagnosisConfidence], ...] = (
    (
        re.compile(r"unable to locate package (\S+)", re.IGNORECASE),
        "missing_package",
        "Package '{match}' is not available in the configured repositories.",
        DiagnosisConfidence.HIGH,
    ),
    (
        re.compile(r"e: (?:package|unable to fetch)", re.IGNORECASE),  # noqa: E501
        "package_manager_failure",
        "The system package manager could not complete the install.",
        DiagnosisConfidence.MEDIUM,
    ),
    (
        re.compile(r"could not find (?:a )?version that satisfies", re.IGNORECASE),
        "incompatible_version",
        "No version matching the requested constraint is available.",
        DiagnosisConfidence.HIGH,
    ),
    (
        re.compile(
            r"(?:permission denied|access is denied|operation not permitted)", re.IGNORECASE
        ),
        "permission_issue",
        "The process lacked permission to complete the operation.",
        DiagnosisConfidence.HIGH,
    ),
    (
        re.compile(
            r"(?:no such file or directory|command not found|not recognized)", re.IGNORECASE
        ),
        "missing_executable",
        "The required executable is not on PATH or does not exist.",
        DiagnosisConfidence.HIGH,
    ),
    (
        re.compile(
            r"(?:connection refused|connection reset|network is unreachable|could not resolve)",
            re.IGNORECASE,
        ),
        "network_connectivity",
        "Network connectivity to the target failed.",
        DiagnosisConfidence.MEDIUM,
    ),
    (
        re.compile(r"(?:disk|no space left on device)", re.IGNORECASE),
        "disk_space",
        "The host is out of writable disk space.",
        DiagnosisConfidence.HIGH,
    ),
    (
        re.compile(r"(?:invalid argument|unrecognized option)", re.IGNORECASE),
        "invalid_argument",
        "The command was invoked with arguments it does not recognize.",
        DiagnosisConfidence.MEDIUM,
    ),
)


class DiagnosisEngine:
    def diagnose(self, signals: FailureSignals) -> Diagnosis:
        if signals.policy_denied:
            return Diagnosis(
                error_category="policy_restriction",
                root_cause="The Policy Engine denied the action.",
                supporting_signals=["policy_denied=True"],
                confidence=DiagnosisConfidence.HIGH,
            )
        if signals.timed_out:
            return Diagnosis(
                error_category="timeout",
                root_cause="The action exceeded its configured timeout.",
                supporting_signals=["timed_out=True"],
                confidence=DiagnosisConfidence.HIGH,
            )

        stderr = signals.stderr or ""
        stdout = signals.stdout or ""
        haystack = f"{stderr}\n{stdout}"

        for pattern, category, template, confidence in _DIAGNOSIS_HINTS:
            match = pattern.search(haystack)
            if match:
                token = match.group(1) if match.groups() else match.group(0)
                return Diagnosis(
                    error_category=category,
                    root_cause=template.format(match=token),
                    supporting_signals=[
                        f"pattern_matched={pattern.pattern!r}",
                        f"token={token!r}",
                    ],
                    confidence=confidence,
                )

        if signals.exit_code is not None and signals.exit_code != 0:
            return Diagnosis(
                error_category=signals.error_category or "nonzero_exit",
                root_cause=f"Command exited with status {signals.exit_code}.",
                supporting_signals=[f"exit_code={signals.exit_code}"],
                confidence=DiagnosisConfidence.LOW,
            )

        return Diagnosis(
            error_category=signals.error_category or "unknown",
            root_cause="No matching diagnostic pattern.",
            supporting_signals=[],
            confidence=DiagnosisConfidence.UNKNOWN,
        )
