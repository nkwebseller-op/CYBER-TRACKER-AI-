from services.self_healing.diagnosis import DiagnosisEngine, FailureSignals
from services.self_healing.models import DiagnosisConfidence


def test_policy_denied_takes_priority():
    diagnosis = DiagnosisEngine().diagnose(
        FailureSignals(policy_denied=True, stderr="permission denied")
    )
    assert diagnosis.error_category == "policy_restriction"
    assert diagnosis.confidence == DiagnosisConfidence.HIGH


def test_timeout_is_recognized():
    diagnosis = DiagnosisEngine().diagnose(FailureSignals(timed_out=True))
    assert diagnosis.error_category == "timeout"


def test_missing_package_extracts_name():
    diagnosis = DiagnosisEngine().diagnose(
        FailureSignals(stderr="E: Unable to locate package dig", exit_code=100)
    )
    assert diagnosis.error_category == "missing_package"
    assert "dig" in diagnosis.root_cause


def test_permission_denied_recognized():
    diagnosis = DiagnosisEngine().diagnose(FailureSignals(stderr="Permission denied"))
    assert diagnosis.error_category == "permission_issue"
    assert diagnosis.confidence == DiagnosisConfidence.HIGH


def test_network_connectivity_recognized():
    diagnosis = DiagnosisEngine().diagnose(FailureSignals(stderr="Network is unreachable"))
    assert diagnosis.error_category == "network_connectivity"


def test_disk_space_recognized():
    diagnosis = DiagnosisEngine().diagnose(FailureSignals(stderr="No space left on device"))
    assert diagnosis.error_category == "disk_space"


def test_missing_executable_recognized():
    diagnosis = DiagnosisEngine().diagnose(FailureSignals(stderr="command not found: nmap"))
    assert diagnosis.error_category == "missing_executable"


def test_nonzero_exit_without_hint_is_low_confidence():
    diagnosis = DiagnosisEngine().diagnose(FailureSignals(exit_code=1, stderr="something odd"))
    assert diagnosis.confidence in (DiagnosisConfidence.LOW, DiagnosisConfidence.UNKNOWN)


def test_no_signals_returns_unknown():
    diagnosis = DiagnosisEngine().diagnose(FailureSignals())
    assert diagnosis.error_category == "unknown"
    assert diagnosis.confidence == DiagnosisConfidence.UNKNOWN


def test_diagnosis_never_fabricates_evidence():
    """A key Phase 13 principle: supporting_signals is only populated
    from real matches, never guessed."""
    diagnosis = DiagnosisEngine().diagnose(FailureSignals())
    assert diagnosis.supporting_signals == []
