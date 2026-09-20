from services.tools.models import ToolRecord, TrustStatus
from services.tools.policy import ToolPolicyGate


def _tool(**overrides) -> ToolRecord:
    defaults = dict(
        name="dig",
        display_name="dig",
        description="DNS tool",
        capabilities=("dns_lookup",),
        supported_platforms=("LINUX", "MACOS"),
        trust_status=TrustStatus.APPROVED,
    )
    defaults.update(overrides)
    return ToolRecord(**defaults)


def test_approved_compatible_tool_is_eligible():
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(), target_platform="LINUX")
    assert decision.eligible is True


def test_verified_but_not_approved_tool_is_not_eligible():
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(trust_status=TrustStatus.VERIFIED))
    assert decision.eligible is False
    assert any("APPROVED" in r for r in decision.reasons)


def test_blocked_tool_is_never_eligible():
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(trust_status=TrustStatus.BLOCKED))
    assert decision.eligible is False


def test_deprecated_tool_is_never_eligible():
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(trust_status=TrustStatus.DEPRECATED))
    assert decision.eligible is False


def test_prohibited_capability_marker_is_never_eligible_even_if_approved():
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(capabilities=("credential_theft",)))
    assert decision.eligible is False


def test_platform_mismatch_is_not_eligible():
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(supported_platforms=("WINDOWS",)), target_platform="LINUX")
    assert decision.eligible is False


def test_no_target_platform_specified_skips_platform_check():
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(supported_platforms=("WINDOWS",)))
    assert decision.eligible is True


def test_popularity_or_availability_never_grants_eligibility_alone():
    """Being on GitHub / widely used isn't part of the model at all — only
    explicit APPROVED trust status, platform match, and no prohibited
    capability marker matter."""
    gate = ToolPolicyGate()
    decision = gate.evaluate(_tool(trust_status=TrustStatus.DISCOVERED))
    assert decision.eligible is False
