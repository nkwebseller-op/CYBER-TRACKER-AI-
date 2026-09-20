from uuid import uuid4

from services.installation.readiness import CheckStatus, ReadinessChecker
from services.policy.engine import TargetScope
from services.tools.models import SourceType, TrustStatus
from services.tools.registry import InMemoryToolRegistry

from tests.installation.helpers import approved_tool

ACTIVE_TARGET = TargetScope(id=uuid4(), is_active=True, expires_at=None)
INACTIVE_TARGET = TargetScope(id=uuid4(), is_active=False, expires_at=None)


async def test_ready_when_everything_checks_out():
    registry = InMemoryToolRegistry()
    tool = await registry.create(approved_tool())
    report = await ReadinessChecker().check(
        registry, tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert report.ready is True


async def test_unknown_tool_is_never_ready():
    registry = InMemoryToolRegistry()
    report = await ReadinessChecker().check(
        registry, uuid4(), target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert report.ready is False
    assert report.tool is None


async def test_not_approved_tool_is_not_ready():
    registry = InMemoryToolRegistry()
    tool = await registry.create(approved_tool(trust_status=TrustStatus.VERIFIED))
    report = await ReadinessChecker().check(
        registry, tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert report.ready is False
    trust_check = next(c for c in report.checks if c.name == "trust_approved")
    assert trust_check.status == CheckStatus.FAIL


async def test_unsupported_platform_is_not_ready():
    registry = InMemoryToolRegistry()
    tool = await registry.create(approved_tool(supported_platforms=("WINDOWS",)))
    report = await ReadinessChecker().check(
        registry, tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert report.ready is False


async def test_untrusted_source_is_not_ready():
    registry = InMemoryToolRegistry()
    from services.tools.models import SourceProvenance

    tool = await registry.create(
        approved_tool(provenance=SourceProvenance(source_type=SourceType.UNKNOWN))
    )
    report = await ReadinessChecker().check(
        registry, tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert report.ready is False


async def test_inactive_target_authorization_blocks_readiness():
    registry = InMemoryToolRegistry()
    tool = await registry.create(approved_tool())
    report = await ReadinessChecker().check(
        registry, tool.id, target_scope=INACTIVE_TARGET, platform="LINUX"
    )
    assert report.ready is False
    auth_check = next(c for c in report.checks if c.name == "target_authorized")
    assert auth_check.status == CheckStatus.FAIL


async def test_missing_license_is_unknown_but_not_critical():
    registry = InMemoryToolRegistry()
    tool = await registry.create(approved_tool(license=None))
    report = await ReadinessChecker().check(
        registry, tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    license_check = next(c for c in report.checks if c.name == "license_known")
    assert license_check.status == CheckStatus.UNKNOWN
    assert license_check.critical is False
    assert report.ready is True


async def test_policy_denies_unregistered_risk_combination():
    """Reuses the real PolicyEngine — CRITICAL risk still requires
    approval, not an outright deny, but a fully inactive target denies."""
    registry = InMemoryToolRegistry()
    tool = await registry.create(approved_tool())
    report = await ReadinessChecker().check(
        registry, tool.id, target_scope=INACTIVE_TARGET, platform="LINUX"
    )
    assert report.policy_decision is not None
    assert report.policy_decision.verdict.value == "DENY"
