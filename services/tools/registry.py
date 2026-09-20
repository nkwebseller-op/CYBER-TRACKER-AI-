"""Tool Intelligence: compatibility, provenance, and install specs for
security tools the platform may eventually invoke.

Phase 1 defines the data shape only. Populating it with real, vetted tools
and wiring it into services/policy.engine.REGISTERED_ACTION_TYPES is the
first task of Phase 2.
"""

from dataclasses import dataclass
from enum import StrEnum


class ToolProvenance(StrEnum):
    OFFICIAL_REPO = "official_repo"
    PACKAGE_MANAGER = "package_manager"
    VERIFIED_VENDOR = "verified_vendor"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    domains: tuple[str, ...]
    provenance: ToolProvenance
    install_command: tuple[str, ...] | None
    supported_platforms: tuple[str, ...]


# Empty by design in Phase 1 — see module docstring.
TOOL_REGISTRY: dict[str, ToolSpec] = {}
