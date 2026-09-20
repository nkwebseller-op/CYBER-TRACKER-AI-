"""Core data models for Tool Installation & Environment Preparation.

Framework/database-independent dataclasses — same split as
services/tools/models.py and services/terminal/models.py. Nothing here is
directly executable: an `InstallationStep` carries a package manager id
and a validated package name/version, never a raw shell string (argv is
only ever produced by services.terminal.command_templates.build_install_
command / build_verification_command, which validate every input).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from services.policy.engine import RiskTier
from services.tools.models import SourceProvenance

__all__ = [
    "DependencyCheck",
    "DependencyStatus",
    "EnvironmentCheck",
    "InstallationAttempt",
    "InstallationPlan",
    "InstallationRequest",
    "InstallationResult",
    "InstallationState",
    "InstallationStep",
    "InstallationVerification",
    "PackageManager",
]


class PackageManager(StrEnum):
    WINGET = "winget"
    APT = "apt"
    DNF = "dnf"
    PACMAN = "pacman"
    BREW = "brew"
    PIP = "pip"
    TERMUX_PKG = "termux_pkg"
    UNKNOWN = "unknown"


class InstallationState(StrEnum):
    DISCOVERED = "DISCOVERED"
    REVIEWING = "REVIEWING"
    DEPENDENCIES_CHECKING = "DEPENDENCIES_CHECKING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    PREPARING = "PREPARING"
    INSTALLING = "INSTALLING"
    VERIFYING = "VERIFYING"
    INSTALLED = "INSTALLED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"


_TERMINAL_STATES = frozenset(
    {
        InstallationState.INSTALLED,
        InstallationState.FAILED,
        InstallationState.BLOCKED,
        InstallationState.CANCELLED,
    }
)


class DependencyStatus(StrEnum):
    """Three-valued, like services.tools.models.VerificationResult — a
    dependency this system cannot actually check is UNKNOWN, never
    fabricated as satisfied."""

    SATISFIED = "satisfied"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DependencyCheck:
    name: str
    required_version: str | None = None
    found_version: str | None = None
    status: DependencyStatus = DependencyStatus.UNKNOWN
    note: str = ""


@dataclass(frozen=True)
class EnvironmentCheck:
    """Read-only introspection of the *server's* environment — detection
    only, never a mutation, so this never needs to go through the Policy
    Engine (the same reasoning Phase 6-8 adapters' `get_capabilities()`
    already relies on)."""

    platform: str
    architecture: str
    shell: str | None
    available_package_managers: tuple[PackageManager, ...] = ()
    python_version: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstallationStep:
    description: str
    package_manager: PackageManager
    action_type: str
    package_name: str
    version: str | None = None


@dataclass
class InstallationPlan:
    tool_id: UUID
    tool_name: str
    platform: str
    architecture: str
    source: SourceProvenance
    version: str | None
    package_manager: PackageManager
    dependencies: list[DependencyCheck] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    installation_steps: list[InstallationStep] = field(default_factory=list)
    verification_steps: list[str] = field(default_factory=list)
    risk_level: RiskTier = RiskTier.MEDIUM
    approval_required: bool = True
    estimated_changes: list[str] = field(default_factory=list)
    rollback_information: str = (
        "No automated rollback in this phase; uninstall via the same package manager."
    )
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class InstallationVerification:
    executable_found: bool | None = None
    version_output: str | None = None
    checks: dict[str, str] = field(default_factory=dict)
    verified: bool = False


@dataclass
class InstallationAttempt:
    attempt_number: int
    started_at: datetime
    completed_at: datetime | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    duration_seconds: float | None = None
    error_category: str | None = None


@dataclass
class InstallationRequest:
    id: UUID = field(default_factory=uuid4)
    tool_id: UUID = field(default_factory=uuid4)
    target_id: UUID | None = None
    session_id: UUID | None = None
    requested_by: str | None = None
    plan: InstallationPlan | None = None
    state: InstallationState = InstallationState.DISCOVERED
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    attempts: list[InstallationAttempt] = field(default_factory=list)
    verification: InstallationVerification | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_terminal(self) -> bool:
        return self.state in _TERMINAL_STATES

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)


@dataclass
class InstallationResult:
    """Returned to API callers — a snapshot, not the mutable request."""

    request_id: UUID
    state: InstallationState
    attempts: list[InstallationAttempt]
    verification: InstallationVerification | None
    error_message: str | None
