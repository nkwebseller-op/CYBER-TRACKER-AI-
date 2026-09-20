"""Pydantic contracts for the Tool Discovery & Trusted Tool Registry API.

Deliberately no endpoint here accepts an entrypoint/argv/install-command
that would make a tool directly executable — see
apps/api/app/api/routes/tools.py's module docstring for why there is no
`POST /execute-tool`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from services.policy.engine import RiskTier
from services.tools.models import (
    SourceType,
    ToolCategory,
    TrustStatus,
    VerificationResult,
    VerificationStage,
)


class ProvenanceResponse(BaseModel):
    source_type: SourceType = Field(alias="sourceType")
    source_url: str | None = Field(default=None, alias="sourceUrl")
    repository_url: str | None = Field(default=None, alias="repositoryUrl")
    documentation_url: str | None = Field(default=None, alias="documentationUrl")
    publisher: str | None = None
    discovered_version: str | None = Field(default=None, alias="discoveredVersion")
    discovered_at: datetime = Field(alias="discoveredAt")

    model_config = ConfigDict(populate_by_name=True)


class VerificationReportResponse(BaseModel):
    results: dict[VerificationStage, VerificationResult] = Field(default_factory=dict)
    notes: dict[VerificationStage, str] = Field(default_factory=dict)
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    overall: VerificationResult = VerificationResult.UNKNOWN

    model_config = ConfigDict(populate_by_name=True)


class ToolResponse(BaseModel):
    id: UUID
    name: str
    display_name: str = Field(alias="displayName")
    description: str
    category: ToolCategory
    capabilities: list[str]
    supported_platforms: list[str] = Field(alias="supportedPlatforms")
    provenance: ProvenanceResponse
    version: str | None = None
    license: str | None = None
    installation_method: str | None = Field(default=None, alias="installationMethod")
    entrypoint: str | None = None
    dependencies: list[str]
    required_permissions: list[str] = Field(alias="requiredPermissions")
    risk_level: RiskTier = Field(alias="riskLevel")
    trust_status: TrustStatus = Field(alias="trustStatus")
    verification: VerificationReportResponse
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class RegisterToolRequest(BaseModel):
    """Registers a candidate as a Tool Registry entry. This only records
    metadata — it never installs or runs anything (see module docstring)."""

    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(alias="displayName", min_length=1, max_length=255)
    description: str = Field(min_length=1)
    category: ToolCategory
    capabilities: list[str] = Field(default_factory=list)
    supported_platforms: list[str] = Field(default_factory=list, alias="supportedPlatforms")
    source_type: SourceType = Field(alias="sourceType")
    source_url: str | None = Field(default=None, alias="sourceUrl")
    repository_url: str | None = Field(default=None, alias="repositoryUrl")
    documentation_url: str | None = Field(default=None, alias="documentationUrl")
    publisher: str | None = None
    version: str | None = None
    license: str | None = None
    installation_method: str | None = Field(default=None, alias="installationMethod")
    dependencies: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list, alias="requiredPermissions")
    risk_level: RiskTier = Field(default=RiskTier.MEDIUM, alias="riskLevel")

    model_config = ConfigDict(populate_by_name=True)


class DiscoverRequest(BaseModel):
    capability: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(populate_by_name=True)


class ToolCandidateResponse(BaseModel):
    name: str
    display_name: str = Field(alias="displayName")
    description: str
    category: ToolCategory
    capabilities: list[str]
    supported_platforms: list[str] = Field(alias="supportedPlatforms")
    provenance: ProvenanceResponse
    version: str | None = None
    license: str | None = None
    installation_method: str | None = Field(default=None, alias="installationMethod")
    dependencies: list[str]
    required_permissions: list[str] = Field(alias="requiredPermissions")
    risk_level: RiskTier = Field(alias="riskLevel")
    selection_rationale: str = Field(alias="selectionRationale")

    model_config = ConfigDict(populate_by_name=True)


class ToolSelectionProposalResponse(BaseModel):
    required_capability: str = Field(alias="requiredCapability")
    reason: str
    expected_platforms: list[str] = Field(alias="expectedPlatforms")
    expected_dependencies: list[str] = Field(alias="expectedDependencies")
    verification_requirements: list[str] = Field(alias="verificationRequirements")
    candidates: list[ToolCandidateResponse]

    model_config = ConfigDict(populate_by_name=True)


class EligibilityResponse(BaseModel):
    eligible: bool
    reasons: list[str]
