"""Pydantic mirrors of packages/shared-types/schemas/*.json.

These are the request/response models used at the API boundary. They must
stay structurally in sync with the JSON Schema source of truth.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SecurityDomain(StrEnum):
    WEB = "web"
    API = "api"
    NETWORK = "network"
    SERVER_CONFIG = "server_config"
    CLOUD = "cloud"
    WIRELESS = "wireless"
    MOBILE = "mobile"
    VULNERABILITY = "vulnerability"
    RECONNAISSANCE = "reconnaissance"
    DEFENSIVE = "defensive"
    OTHER = "other"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyVerdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PlannedAction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    action_type: str
    domain: SecurityDomain
    target_id: UUID
    risk_tier: RiskTier
    parameters: dict
    rationale: str | None = None
    created_at: datetime


class PolicyDecision(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_id: UUID
    verdict: PolicyVerdict
    reasons: list[str]
    requires_approval: bool
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    decided_at: datetime


class HealthStatus(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
