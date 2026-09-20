import uuid
from datetime import datetime, timedelta, timezone

from services.policy.engine import ActionRequest, PolicyEngine, PolicyVerdict, RiskTier, TargetScope


def _target(*, is_active=True, expires_at=None) -> TargetScope:
    return TargetScope(id=uuid.uuid4(), is_active=is_active, expires_at=expires_at)


def test_denies_when_target_inactive():
    engine = PolicyEngine()
    request = ActionRequest(
        action_id=uuid.uuid4(),
        action_type="recon.dns_lookup",
        risk_tier=RiskTier.LOW,
        target=_target(is_active=False),
    )
    decision = engine.evaluate(request)
    assert decision.verdict == PolicyVerdict.DENY


def test_denies_when_target_expired():
    engine = PolicyEngine()
    request = ActionRequest(
        action_id=uuid.uuid4(),
        action_type="recon.dns_lookup",
        risk_tier=RiskTier.LOW,
        target=_target(expires_at=datetime.now(timezone.utc) - timedelta(days=1)),
    )
    decision = engine.evaluate(request)
    assert decision.verdict == PolicyVerdict.DENY


def test_denies_unregistered_action_type_even_when_in_scope():
    engine = PolicyEngine()
    request = ActionRequest(
        action_id=uuid.uuid4(),
        action_type="anything.unregistered",
        risk_tier=RiskTier.LOW,
        target=_target(),
    )
    decision = engine.evaluate(request)
    assert decision.verdict == PolicyVerdict.DENY
