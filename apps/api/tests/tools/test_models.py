from services.tools.models import (
    ToolCandidate,
    ToolRecord,
    VerificationReport,
    VerificationResult,
    VerificationStage,
)


def test_verification_overall_is_unknown_when_no_stages_ran():
    report = VerificationReport()
    assert report.overall() == VerificationResult.UNKNOWN


def test_verification_overall_is_verified_when_all_stages_verified():
    report = VerificationReport(
        results={
            VerificationStage.COLLECT_METADATA: VerificationResult.VERIFIED,
            VerificationStage.VERIFY_SOURCE: VerificationResult.VERIFIED,
        }
    )
    assert report.overall() == VerificationResult.VERIFIED


def test_verification_overall_prioritizes_failed_over_everything():
    report = VerificationReport(
        results={
            VerificationStage.COLLECT_METADATA: VerificationResult.VERIFIED,
            VerificationStage.VERIFY_SOURCE: VerificationResult.FAILED,
            VerificationStage.CHECK_LICENSE: VerificationResult.UNKNOWN,
        }
    )
    assert report.overall() == VerificationResult.FAILED


def test_verification_overall_prioritizes_unknown_over_unverified():
    report = VerificationReport(
        results={
            VerificationStage.COLLECT_METADATA: VerificationResult.UNVERIFIED,
            VerificationStage.VERIFY_SOURCE: VerificationResult.UNKNOWN,
        }
    )
    assert report.overall() == VerificationResult.UNKNOWN


def test_tool_record_from_candidate_starts_discovered():
    from services.tools.models import TrustStatus

    candidate = ToolCandidate(name="dig", display_name="dig", description="DNS lookup tool")
    record = ToolRecord.from_candidate(candidate)

    assert record.name == "dig"
    assert record.trust_status == TrustStatus.DISCOVERED
