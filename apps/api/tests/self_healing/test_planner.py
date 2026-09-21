from services.self_healing.models import Diagnosis, DiagnosisConfidence, HealingStrategyKind
from services.self_healing.planner import HealingPlanner, HealingPlannerConfig


def _diagnosis(category: str, confidence=DiagnosisConfidence.HIGH) -> Diagnosis:
    return Diagnosis(error_category=category, confidence=confidence, root_cause="test")


def test_policy_restriction_always_escalates():
    strategy = HealingPlanner().propose(_diagnosis("policy_restriction"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.ESCALATE_TO_USER
    assert strategy.requires_user_approval is True


def test_timeout_first_attempt_adjusts_timeout():
    strategy = HealingPlanner().propose(_diagnosis("timeout"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.ADJUST_TIMEOUT
    assert strategy.parameters.get("timeout_multiplier", 0) > 1


def test_timeout_after_max_retries_escalates():
    planner = HealingPlanner(HealingPlannerConfig(max_retries=1))
    strategy = planner.propose(_diagnosis("timeout"), retries_used=2)
    assert strategy.kind == HealingStrategyKind.ESCALATE_TO_USER


def test_missing_package_proposes_install_with_approval():
    strategy = HealingPlanner().propose(_diagnosis("missing_package"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.INSTALL_MISSING_DEPENDENCY
    assert strategy.requires_user_approval is True
    assert strategy.requires_policy_recheck is True


def test_missing_executable_proposes_install():
    strategy = HealingPlanner().propose(_diagnosis("missing_executable"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.INSTALL_MISSING_DEPENDENCY


def test_network_connectivity_retries_with_backoff():
    strategy = HealingPlanner().propose(_diagnosis("network_connectivity"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.RETRY_WITH_BACKOFF
    assert strategy.parameters.get("backoff_seconds", 0) > 0


def test_repeated_category_triggers_abandon():
    strategy = HealingPlanner().propose(
        _diagnosis("missing_executable"),
        retries_used=1,
        prior_categories=["missing_executable"],
    )
    assert strategy.kind == HealingStrategyKind.ABANDON


def test_incompatible_version_proposes_alternative_tool():
    strategy = HealingPlanner().propose(_diagnosis("incompatible_version"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.USE_ALTERNATIVE_TOOL


def test_permission_issue_escalates():
    strategy = HealingPlanner().propose(_diagnosis("permission_issue"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.ESCALATE_TO_USER


def test_disk_space_escalates():
    strategy = HealingPlanner().propose(_diagnosis("disk_space"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.ESCALATE_TO_USER


def test_invalid_argument_reduces_scope():
    strategy = HealingPlanner().propose(_diagnosis("invalid_argument"), retries_used=0)
    assert strategy.kind == HealingStrategyKind.REDUCE_SCOPE
    assert strategy.requires_user_approval is True


def test_low_confidence_diagnosis_escalates():
    strategy = HealingPlanner().propose(
        _diagnosis("unknown", DiagnosisConfidence.UNKNOWN), retries_used=0
    )
    assert strategy.kind == HealingStrategyKind.ESCALATE_TO_USER


def test_healing_never_proposes_something_outside_the_strategy_vocabulary():
    """The full strategy set is fixed at StrEnum level, so anything
    HealingPlanner returns is by construction one of the reviewed
    kinds."""
    for category in ("missing_package", "policy_restriction", "timeout", "network_connectivity",
                     "incompatible_version", "permission_issue", "disk_space",
                     "invalid_argument", "unknown", "some_novel_category"):
        strategy = HealingPlanner().propose(_diagnosis(category), retries_used=0)
        assert strategy.kind in list(HealingStrategyKind)
