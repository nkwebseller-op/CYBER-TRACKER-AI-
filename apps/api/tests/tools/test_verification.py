from services.tools.models import (
    SourceProvenance,
    SourceType,
    ToolCandidate,
    VerificationResult,
    VerificationStage,
)
from services.tools.verification import VerificationPipeline

from tests.terminal.helpers import RecordingAuditSink


def _candidate(**overrides) -> ToolCandidate:
    defaults = dict(
        name="dig",
        display_name="dig",
        description="DNS lookup tool",
        provenance=SourceProvenance(
            source_type=SourceType.OFFICIAL_WEBSITE, source_url="https://isc.org"
        ),
        version="9.18",
        license="MPL-2.0",
        supported_platforms=("LINUX", "MACOS"),
    )
    defaults.update(overrides)
    return ToolCandidate(**defaults)


def test_well_documented_candidate_verifies_cleanly():
    pipeline = VerificationPipeline()
    report = pipeline.verify(_candidate())

    assert report.results[VerificationStage.COLLECT_METADATA] == VerificationResult.VERIFIED
    assert report.results[VerificationStage.VERIFY_SOURCE] == VerificationResult.VERIFIED
    assert report.results[VerificationStage.VERIFY_VERSION] == VerificationResult.VERIFIED
    assert report.results[VerificationStage.CHECK_PLATFORM] == VerificationResult.VERIFIED
    assert report.results[VerificationStage.CHECK_LICENSE] == VerificationResult.VERIFIED
    assert report.overall() == VerificationResult.VERIFIED
    assert report.completed_at is not None


def test_missing_version_is_unknown_not_fabricated():
    pipeline = VerificationPipeline()
    report = pipeline.verify(_candidate(version=None))
    assert report.results[VerificationStage.VERIFY_VERSION] == VerificationResult.UNKNOWN


def test_missing_license_is_unknown_not_fabricated():
    pipeline = VerificationPipeline()
    report = pipeline.verify(_candidate(license=None))
    assert report.results[VerificationStage.CHECK_LICENSE] == VerificationResult.UNKNOWN


def test_unknown_source_type_is_not_verified():
    pipeline = VerificationPipeline()
    candidate = _candidate(provenance=SourceProvenance(source_type=SourceType.UNKNOWN))
    report = pipeline.verify(candidate)
    assert report.results[VerificationStage.VERIFY_SOURCE] == VerificationResult.UNKNOWN


def test_other_reputable_source_is_unverified_not_verified():
    pipeline = VerificationPipeline()
    candidate = _candidate(
        provenance=SourceProvenance(
            source_type=SourceType.OTHER_REPUTABLE, source_url="https://example.org"
        )
    )
    report = pipeline.verify(candidate)
    assert report.results[VerificationStage.VERIFY_SOURCE] == VerificationResult.UNVERIFIED


def test_unrecognized_platform_is_unverified():
    pipeline = VerificationPipeline()
    candidate = _candidate(supported_platforms=("PLAYSTATION",))
    report = pipeline.verify(candidate)
    assert report.results[VerificationStage.CHECK_PLATFORM] == VerificationResult.UNVERIFIED


def test_no_platforms_declared_is_unknown():
    pipeline = VerificationPipeline()
    candidate = _candidate(supported_platforms=())
    report = pipeline.verify(candidate)
    assert report.results[VerificationStage.CHECK_PLATFORM] == VerificationResult.UNKNOWN


def test_dependencies_declared_are_unverified_not_verified():
    pipeline = VerificationPipeline()
    candidate = _candidate(dependencies=("libpcap",))
    report = pipeline.verify(candidate)
    assert report.results[VerificationStage.CHECK_DEPENDENCIES] == VerificationResult.UNVERIFIED


def test_no_dependencies_is_verified():
    pipeline = VerificationPipeline()
    candidate = _candidate(dependencies=())
    report = pipeline.verify(candidate)
    assert report.results[VerificationStage.CHECK_DEPENDENCIES] == VerificationResult.VERIFIED


def test_prohibited_capability_marker_fails_security_review():
    pipeline = VerificationPipeline()
    candidate = _candidate(capabilities=("credential_theft",))
    report = pipeline.verify(candidate)
    assert report.results[VerificationStage.SECURITY_POLICY_REVIEW] == VerificationResult.FAILED
    assert report.overall() == VerificationResult.FAILED


def test_verification_emits_started_and_completed_audit_events():
    sink = RecordingAuditSink()
    pipeline = VerificationPipeline(audit_sink=sink)
    pipeline.verify(_candidate())

    assert "tool.verification.started" in sink.event_types
    assert "tool.verification.completed" in sink.event_types


def test_verification_emits_failed_event_for_failed_overall():
    sink = RecordingAuditSink()
    pipeline = VerificationPipeline(audit_sink=sink)
    pipeline.verify(_candidate(capabilities=("persistence",)))

    assert "tool.verification.failed" in sink.event_types
