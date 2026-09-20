"""Pydantic contracts for the Tool Installation & Environment Preparation
API. No endpoint here accepts raw argv or a shell string — installation
requests only ever carry a `toolId` + `targetId` + `platform`; the actual
command is built exclusively by services.terminal.command_templates."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from services.installation.models import InstallationState, PackageManager
from services.policy.engine import RiskTier


class ReadinessRequest(BaseModel):
    tool_id: UUID = Field(alias="toolId")
    target_id: UUID = Field(alias="targetId")
    platform: str

    model_config = ConfigDict(populate_by_name=True)


class ReadinessCheckResponse(BaseModel):
    name: str
    status: str
    detail: str
    critical: bool

    model_config = ConfigDict(populate_by_name=True)


class ReadinessResponse(BaseModel):
    ready: bool
    checks: list[ReadinessCheckResponse]

    model_config = ConfigDict(populate_by_name=True)


class RequestInstallationRequest(BaseModel):
    tool_id: UUID = Field(alias="toolId")
    target_id: UUID = Field(alias="targetId")
    platform: str
    requested_by: str | None = Field(default=None, alias="requestedBy")

    model_config = ConfigDict(populate_by_name=True)


class DependencyCheckResponse(BaseModel):
    name: str
    required_version: str | None = Field(default=None, alias="requiredVersion")
    found_version: str | None = Field(default=None, alias="foundVersion")
    status: str
    note: str

    model_config = ConfigDict(populate_by_name=True)


class InstallationStepResponse(BaseModel):
    description: str
    package_manager: PackageManager = Field(alias="packageManager")
    action_type: str = Field(alias="actionType")
    package_name: str = Field(alias="packageName")
    version: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class InstallationPlanResponse(BaseModel):
    tool_id: UUID = Field(alias="toolId")
    tool_name: str = Field(alias="toolName")
    platform: str
    architecture: str
    version: str | None = None
    package_manager: PackageManager = Field(alias="packageManager")
    dependencies: list[DependencyCheckResponse]
    prerequisites: list[str]
    required_permissions: list[str] = Field(alias="requiredPermissions")
    installation_steps: list[InstallationStepResponse] = Field(alias="installationSteps")
    verification_steps: list[str] = Field(alias="verificationSteps")
    risk_level: RiskTier = Field(alias="riskLevel")
    approval_required: bool = Field(alias="approvalRequired")
    estimated_changes: list[str] = Field(alias="estimatedChanges")
    rollback_information: str = Field(alias="rollbackInformation")

    model_config = ConfigDict(populate_by_name=True)


class InstallationAttemptResponse(BaseModel):
    attempt_number: int = Field(alias="attemptNumber")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    exit_code: int | None = Field(default=None, alias="exitCode")
    stdout: str | None = None
    stderr: str | None = None
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")
    error_category: str | None = Field(default=None, alias="errorCategory")

    model_config = ConfigDict(populate_by_name=True)


class InstallationVerificationResponse(BaseModel):
    executable_found: bool | None = Field(default=None, alias="executableFound")
    version_output: str | None = Field(default=None, alias="versionOutput")
    checks: dict[str, str]
    verified: bool

    model_config = ConfigDict(populate_by_name=True)


class InstallationRequestResponse(BaseModel):
    id: UUID
    tool_id: UUID = Field(alias="toolId")
    target_id: UUID | None = Field(default=None, alias="targetId")
    state: InstallationState
    plan: InstallationPlanResponse | None = None
    approved_by: str | None = Field(default=None, alias="approvedBy")
    approved_at: datetime | None = Field(default=None, alias="approvedAt")
    rejection_reason: str | None = Field(default=None, alias="rejectionReason")
    attempts: list[InstallationAttemptResponse]
    verification: InstallationVerificationResponse | None = None
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class ApproveInstallationRequest(BaseModel):
    approved_by: str = Field(alias="approvedBy", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class RejectInstallationRequest(BaseModel):
    reason: str = Field(min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class StartInstallationRequest(BaseModel):
    target_id: UUID = Field(alias="targetId")

    model_config = ConfigDict(populate_by_name=True)
