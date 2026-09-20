import pytest
from services.agent_orchestrator.analysis import ResultAnalyzer, VerificationEngine
from services.agent_orchestrator.models import EvidenceKind


def test_observe_produces_observation_kind():
    analyzer = ResultAnalyzer()
    evidence = analyzer.observe(action_id=None, summary="saw something")
    assert evidence.kind == EvidenceKind.OBSERVATION


def test_propose_finding_is_unverified():
    analyzer = ResultAnalyzer()
    finding = analyzer.propose_finding(action_id=None, summary="looks vulnerable")
    assert finding.kind == EvidenceKind.FINDING


def test_verify_without_corroboration_stays_a_finding():
    analyzer = ResultAnalyzer()
    finding = analyzer.propose_finding(action_id=None, summary="looks vulnerable")
    verified = VerificationEngine().verify(finding, corroborating_evidence=[])
    assert verified.kind == EvidenceKind.FINDING


def test_verify_with_corroboration_becomes_verified_finding():
    analyzer = ResultAnalyzer()
    finding = analyzer.propose_finding(action_id=None, summary="looks vulnerable")
    verified = VerificationEngine().verify(finding, corroborating_evidence=["independent check"])
    assert verified.kind == EvidenceKind.VERIFIED_FINDING


def test_verify_rejects_non_finding_evidence():
    analyzer = ResultAnalyzer()
    observation = analyzer.observe(action_id=None, summary="raw observation")
    with pytest.raises(ValueError):
        VerificationEngine().verify(observation, corroborating_evidence=["x"])


def test_command_success_is_never_equated_with_verification():
    """The core Phase 12 principle: an OBSERVATION from a successful
    command is not, by itself, a VERIFIED_FINDING."""
    analyzer = ResultAnalyzer()
    observation = analyzer.observe(action_id=None, summary="command exited 0")
    assert observation.kind != EvidenceKind.VERIFIED_FINDING
    assert observation.kind == EvidenceKind.OBSERVATION
