"""Verification pipeline.

    DISCOVER (done by ToolDiscoveryService)
      -> COLLECT_METADATA
      -> VERIFY_SOURCE
      -> VERIFY_VERSION
      -> CHECK_PLATFORM
      -> CHECK_LICENSE
      -> CHECK_DEPENDENCIES
      -> SECURITY_POLICY_REVIEW
      -> trust status

Every stage operates only on information already present on the
candidate/tool — this phase performs no live network calls to verify a
signature, hash, or upstream release, so a stage is marked
VerificationResult.UNKNOWN whenever the necessary information genuinely
isn't available, rather than guessing. This is intentional: fabricating a
positive verification result would be worse than admitting "unknown."
"""

from datetime import UTC, datetime

from services.terminal.audit import AuditEvent, AuditSink, LoggingAuditSink
from services.tools.audit_events import (
    TOOL_VERIFICATION_COMPLETED,
    TOOL_VERIFICATION_FAILED,
    TOOL_VERIFICATION_STARTED,
)
from services.tools.models import (
    SourceType,
    ToolCandidate,
    ToolRecord,
    VerificationReport,
    VerificationResult,
    VerificationStage,
)

# A capability containing any of these substrings is never eligible for
# VERIFIED trust regardless of source — this is a hard content-based
# refusal, independent of (and in addition to) the real PolicyEngine.
_PROHIBITED_CAPABILITY_MARKERS = (
    "credential_theft",
    "credential_dump",
    "persistence",
    "evasion",
    "exploit_auto",
    "av_bypass",
    "security_control_bypass",
)

_TRUSTED_SOURCE_TYPES = frozenset(
    {SourceType.OFFICIAL_WEBSITE, SourceType.OFFICIAL_GITHUB, SourceType.OFFICIAL_PACKAGE_REGISTRY}
)

_SUPPORTED_PLATFORMS = frozenset({"WINDOWS", "LINUX", "MACOS", "ANDROID_TERMUX"})


class VerificationPipeline:
    def __init__(self, *, audit_sink: AuditSink | None = None) -> None:
        self._audit = audit_sink or LoggingAuditSink()

    def verify(self, subject: ToolCandidate | ToolRecord) -> VerificationReport:
        self._emit(TOOL_VERIFICATION_STARTED, subject)
        report = VerificationReport()

        self._collect_metadata(subject, report)
        self._verify_source(subject, report)
        self._verify_version(subject, report)
        self._check_platform(subject, report)
        self._check_license(subject, report)
        self._check_dependencies(subject, report)
        self._security_policy_review(subject, report)

        report.completed_at = datetime.now(UTC)

        if report.overall() == VerificationResult.FAILED:
            self._emit(TOOL_VERIFICATION_FAILED, subject, overall=report.overall().value)
        else:
            self._emit(TOOL_VERIFICATION_COMPLETED, subject, overall=report.overall().value)
        return report

    # --- stages -----------------------------------------------------------

    def _collect_metadata(self, subject, report: VerificationReport) -> None:
        has_basics = bool(subject.name) and bool(subject.description)
        report.results[VerificationStage.COLLECT_METADATA] = (
            VerificationResult.VERIFIED if has_basics else VerificationResult.UNKNOWN
        )
        report.notes[VerificationStage.COLLECT_METADATA] = (
            "Name and description present." if has_basics else "Missing name or description."
        )

    def _verify_source(self, subject, report: VerificationReport) -> None:
        provenance = subject.provenance
        if provenance.source_type in _TRUSTED_SOURCE_TYPES and provenance.source_url:
            result = VerificationResult.VERIFIED
            note = f"Source type '{provenance.source_type.value}' with a recorded URL."
        elif provenance.source_type == SourceType.OTHER_REPUTABLE:
            result = VerificationResult.UNVERIFIED
            note = "Source is reputable but not an official first-party source."
        else:
            result = VerificationResult.UNKNOWN
            note = "Source type is unknown or lacks a recorded URL."
        report.results[VerificationStage.VERIFY_SOURCE] = result
        report.notes[VerificationStage.VERIFY_SOURCE] = note

    def _verify_version(self, subject, report: VerificationReport) -> None:
        if subject.version:
            result, note = VerificationResult.VERIFIED, f"Discovered version '{subject.version}'."
        else:
            result, note = VerificationResult.UNKNOWN, "No version information was discovered."
        report.results[VerificationStage.VERIFY_VERSION] = result
        report.notes[VerificationStage.VERIFY_VERSION] = note

    def _check_platform(self, subject, report: VerificationReport) -> None:
        platforms = set(subject.supported_platforms)
        if not platforms:
            result, note = VerificationResult.UNKNOWN, "No supported platforms were declared."
        elif platforms.issubset(_SUPPORTED_PLATFORMS):
            result = VerificationResult.VERIFIED
            note = f"Declared platforms {sorted(platforms)} are all recognized."
        else:
            unrecognized = sorted(platforms - _SUPPORTED_PLATFORMS)
            result = VerificationResult.UNVERIFIED
            note = f"Declared unrecognized platform(s): {unrecognized}."
        report.results[VerificationStage.CHECK_PLATFORM] = result
        report.notes[VerificationStage.CHECK_PLATFORM] = note

    def _check_license(self, subject, report: VerificationReport) -> None:
        if subject.license:
            result, note = VerificationResult.VERIFIED, f"Declared license '{subject.license}'."
        else:
            result, note = VerificationResult.UNKNOWN, "No license information was discovered."
        report.results[VerificationStage.CHECK_LICENSE] = result
        report.notes[VerificationStage.CHECK_LICENSE] = note

    def _check_dependencies(self, subject, report: VerificationReport) -> None:
        # This phase never resolves/downloads dependencies — it only
        # records whether the candidate declared any, which is honestly
        # all that can be "verified" without executing anything.
        if subject.dependencies:
            result = VerificationResult.UNVERIFIED
            note = (
                f"Declares {len(subject.dependencies)} dependency(ies); "
                "not independently resolved."
            )
        else:
            result, note = VerificationResult.VERIFIED, "No external dependencies declared."
        report.results[VerificationStage.CHECK_DEPENDENCIES] = result
        report.notes[VerificationStage.CHECK_DEPENDENCIES] = note

    def _security_policy_review(self, subject, report: VerificationReport) -> None:
        capability_text = " ".join(subject.capabilities).lower()
        hit = next((m for m in _PROHIBITED_CAPABILITY_MARKERS if m in capability_text), None)
        if hit:
            result = VerificationResult.FAILED
            note = f"Declares prohibited capability marker '{hit}'."
        else:
            result = VerificationResult.VERIFIED
            note = "No prohibited capability markers declared."
        report.results[VerificationStage.SECURITY_POLICY_REVIEW] = result
        report.notes[VerificationStage.SECURITY_POLICY_REVIEW] = note

    def _emit(self, event_type: str, subject, **data: object) -> None:
        self._audit.emit(
            AuditEvent(
                event_type=event_type,
                session_id=None,
                command_id=None,
                task_id=None,
                data={"tool_name": subject.name, **data},
            )
        )
