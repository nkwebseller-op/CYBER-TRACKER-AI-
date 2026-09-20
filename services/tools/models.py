"""Core data models for Tool Discovery & the Trusted Tool Registry.

Framework/database-independent dataclasses — the same split the rest of
services/ uses (see services/terminal/models.py): apps/api owns the ORM
mapping (app/db/models.py) and translates to/from these shapes.

Trust vs. authorization, kept deliberately separate per the phase spec:
`TrustStatus` describes what the registry believes about a tool's
provenance and integrity. It never grants permission to run anything —
that still requires the real `services.policy.engine.PolicyEngine`,
target authorization, and (for medium+ risk) explicit user approval,
exactly as every other action in this system does. A tool at
`TrustStatus.APPROVED` is *eligible* to be considered; it is not
authorized until the policy engine says so at execution time.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from services.policy.engine import RiskTier

# Re-exported so callers of services.tools don't also need to import
# services.policy.engine just for the risk vocabulary already in use
# everywhere else in this system.
__all__ = [
    "ApprovalRequirement",
    "RiskTier",
    "SourceProvenance",
    "SourceType",
    "ToolCandidate",
    "ToolCategory",
    "ToolRecord",
    "TrustStatus",
    "VerificationReport",
    "VerificationResult",
    "VerificationStage",
]


class ToolCategory(StrEnum):
    NETWORK_DIAGNOSTICS = "network_diagnostics"
    WEB_API_TESTING = "web_api_testing"
    VULNERABILITY_ASSESSMENT = "vulnerability_assessment"
    DNS_DOMAIN_ANALYSIS = "dns_domain_analysis"
    INFRASTRUCTURE_DIAGNOSTICS = "infrastructure_diagnostics"
    CLOUD_SECURITY = "cloud_security"
    MOBILE_SECURITY = "mobile_security"
    WIRELESS_DIAGNOSTICS = "wireless_diagnostics"
    PACKET_TRAFFIC_ANALYSIS = "packet_traffic_analysis"
    LOG_ANALYSIS = "log_analysis"
    SYSTEM_DIAGNOSTICS = "system_diagnostics"
    DEFENSIVE_MONITORING = "defensive_monitoring"
    OSINT = "osint"
    DEVELOPER_UTILITIES = "developer_utilities"


# Preference order for trustworthy provenance — see module docstring in
# services/tools/discovery.py for how this is used (never treats a mirror
# as trusted just because it has the expected filename).
class SourceType(StrEnum):
    OFFICIAL_WEBSITE = "official_website"
    OFFICIAL_GITHUB = "official_github"
    OFFICIAL_PACKAGE_REGISTRY = "official_package_registry"
    OTHER_REPUTABLE = "other_reputable"
    UNKNOWN = "unknown"


SOURCE_TRUST_ORDER: tuple[SourceType, ...] = (
    SourceType.OFFICIAL_WEBSITE,
    SourceType.OFFICIAL_GITHUB,
    SourceType.OFFICIAL_PACKAGE_REGISTRY,
    SourceType.OTHER_REPUTABLE,
    SourceType.UNKNOWN,
)


class TrustStatus(StrEnum):
    UNKNOWN = "unknown"
    DISCOVERED = "discovered"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    APPROVED = "approved"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"


class ApprovalRequirement(StrEnum):
    NONE = "none"
    USER_APPROVAL = "user_approval"
    ADMIN_APPROVAL = "admin_approval"


class VerificationStage(StrEnum):
    COLLECT_METADATA = "collect_metadata"
    VERIFY_SOURCE = "verify_source"
    VERIFY_VERSION = "verify_version"
    CHECK_PLATFORM = "check_platform"
    CHECK_LICENSE = "check_license"
    CHECK_DEPENDENCIES = "check_dependencies"
    SECURITY_POLICY_REVIEW = "security_policy_review"


class VerificationResult(StrEnum):
    """Three-valued, deliberately: a stage that could not be checked is
    UNKNOWN, never fabricated as VERIFIED. See services/tools/verification.py."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceProvenance:
    """Answers "where did this tool come from" — stored with every
    discovered tool, never inferred after the fact."""

    source_type: SourceType
    source_url: str | None = None
    repository_url: str | None = None
    documentation_url: str | None = None
    publisher: str | None = None
    discovered_version: str | None = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class VerificationReport:
    """Per-stage verification outcome. `notes` carries a short, factual
    reason for each result — never a fabricated justification."""

    results: dict[VerificationStage, VerificationResult] = field(default_factory=dict)
    notes: dict[VerificationStage, str] = field(default_factory=dict)
    completed_at: datetime | None = None

    def overall(self) -> VerificationResult:
        """UNKNOWN/blank until every stage has run. FAILED beats UNKNOWN
        beats UNVERIFIED beats VERIFIED — the most cautious result wins."""
        if not self.results:
            return VerificationResult.UNKNOWN
        values = set(self.results.values())
        if VerificationResult.FAILED in values:
            return VerificationResult.FAILED
        if VerificationResult.UNKNOWN in values:
            return VerificationResult.UNKNOWN
        if VerificationResult.UNVERIFIED in values:
            return VerificationResult.UNVERIFIED
        return VerificationResult.VERIFIED


@dataclass
class ToolCandidate:
    """An unregistered, discovered-but-not-yet-persisted tool proposal —
    the output of ToolDiscoveryService / an AI selection proposal. Never
    directly executable: it has no entrypoint the terminal engine accepts,
    only descriptive fields for a human (or the registry) to evaluate."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.DEVELOPER_UTILITIES
    capabilities: tuple[str, ...] = ()
    supported_platforms: tuple[str, ...] = ()
    provenance: SourceProvenance = field(
        default_factory=lambda: SourceProvenance(source_type=SourceType.UNKNOWN)
    )
    version: str | None = None
    license: str | None = None
    installation_method: str | None = None
    dependencies: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    risk_level: RiskTier = RiskTier.MEDIUM
    capability_requested: str = ""
    # Factual, capability-based — e.g. "declares dns_lookup capability and
    # supports LINUX/MACOS/WINDOWS". Never a numerical "best tool" score.
    selection_rationale: str = ""
    verification: VerificationReport = field(default_factory=VerificationReport)


@dataclass
class ToolRecord:
    """A persisted Tool Registry entry. Mirrors app/db/models.py::Tool —
    apps/api translates between the two at the persistence boundary."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.DEVELOPER_UTILITIES
    capabilities: tuple[str, ...] = ()
    supported_platforms: tuple[str, ...] = ()
    provenance: SourceProvenance = field(
        default_factory=lambda: SourceProvenance(source_type=SourceType.UNKNOWN)
    )
    version: str | None = None
    license: str | None = None
    installation_method: str | None = None
    entrypoint: str | None = None
    dependencies: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    risk_level: RiskTier = RiskTier.MEDIUM
    approval_requirement: ApprovalRequirement = ApprovalRequirement.USER_APPROVAL
    trust_status: TrustStatus = TrustStatus.DISCOVERED
    verification: VerificationReport = field(default_factory=VerificationReport)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_candidate(cls, candidate: ToolCandidate) -> "ToolRecord":
        return cls(
            name=candidate.name,
            display_name=candidate.display_name,
            description=candidate.description,
            category=candidate.category,
            capabilities=candidate.capabilities,
            supported_platforms=candidate.supported_platforms,
            provenance=candidate.provenance,
            version=candidate.version,
            license=candidate.license,
            installation_method=candidate.installation_method,
            dependencies=candidate.dependencies,
            required_permissions=candidate.required_permissions,
            risk_level=candidate.risk_level,
            trust_status=TrustStatus.DISCOVERED,
            verification=candidate.verification,
        )
