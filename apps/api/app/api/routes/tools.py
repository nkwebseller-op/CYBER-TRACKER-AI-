"""Tool Discovery & Trusted Tool Registry API.

    "Need a tool for DNS diagnostics"
          |
    POST /api/tools/discover        -> structured candidates (never a URL
          |                             to blindly fetch-and-run)
    POST /api/tools                 -> register a chosen candidate
          |                             (metadata only, trust=DISCOVERED)
    POST /api/tools/{id}/verify     -> run the verification pipeline
          |
    POST /api/tools/{id}/approve    -> explicit human approval
          |                             (still not execution authorization)
    GET  /api/tools/{id}/eligibility -> platform/capability/trust pre-check

There is intentionally no `POST /execute-tool` or any endpoint that runs a
registered tool. Execution remains the exclusive responsibility of the
existing, unchanged TerminalEngine + PolicyEngine — a tool being APPROVED
here only makes it *eligible* to be proposed for an action; actually
running anything still requires a real target, a real PolicyDecision, and
(for medium+ risk) explicit per-action approval, exactly as today.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from services.tools.discovery import ToolDiscoveryService
from services.tools.errors import ToolRegistryError
from services.tools.models import (
    SourceProvenance,
    ToolCandidate,
    ToolCategory,
    ToolRecord,
    TrustStatus,
    VerificationReport,
)
from services.tools.policy import ToolPolicyGate
from services.tools.proposal import build_tool_selection_proposal
from services.tools.registry import ToolRegistry
from services.tools.verification import VerificationPipeline

from app.core.tools import (
    get_discovery_service,
    get_policy_gate,
    get_tool_registry,
    get_verification_pipeline,
)
from app.schemas.tools import (
    DiscoverRequest,
    EligibilityResponse,
    ProvenanceResponse,
    RegisterToolRequest,
    ToolCandidateResponse,
    ToolResponse,
    ToolSelectionProposalResponse,
    VerificationReportResponse,
)

router = APIRouter(prefix="/tools", tags=["tools"])

_ERROR_STATUS_BY_CODE = {
    "tool_not_found": 404,
    "duplicate_tool": 409,
    "invalid_candidate": 422,
    "capability_prohibited": 403,
    "invalid_trust_transition": 409,
}


def _http_error(exc: ToolRegistryError) -> HTTPException:
    status_code = _ERROR_STATUS_BY_CODE.get(exc.code.value, 400)
    detail = {"code": exc.code.value, "message": str(exc)}
    return HTTPException(status_code=status_code, detail=detail)


def _provenance_response(provenance: SourceProvenance) -> ProvenanceResponse:
    return ProvenanceResponse(
        sourceType=provenance.source_type,
        sourceUrl=provenance.source_url,
        repositoryUrl=provenance.repository_url,
        documentationUrl=provenance.documentation_url,
        publisher=provenance.publisher,
        discoveredVersion=provenance.discovered_version,
        discoveredAt=provenance.discovered_at,
    )


def _verification_response(report: VerificationReport) -> VerificationReportResponse:
    return VerificationReportResponse(
        results=dict(report.results),
        notes=dict(report.notes),
        completedAt=report.completed_at,
        overall=report.overall(),
    )


def _tool_response(tool: ToolRecord) -> ToolResponse:
    return ToolResponse(
        id=tool.id,
        name=tool.name,
        displayName=tool.display_name,
        description=tool.description,
        category=tool.category,
        capabilities=list(tool.capabilities),
        supportedPlatforms=list(tool.supported_platforms),
        provenance=_provenance_response(tool.provenance),
        version=tool.version,
        license=tool.license,
        installationMethod=tool.installation_method,
        entrypoint=tool.entrypoint,
        dependencies=list(tool.dependencies),
        requiredPermissions=list(tool.required_permissions),
        riskLevel=tool.risk_level,
        trustStatus=tool.trust_status,
        verification=_verification_response(tool.verification),
        createdAt=tool.created_at,
        updatedAt=tool.updated_at,
    )


def _candidate_response(candidate: ToolCandidate) -> ToolCandidateResponse:
    return ToolCandidateResponse(
        name=candidate.name,
        displayName=candidate.display_name,
        description=candidate.description,
        category=candidate.category,
        capabilities=list(candidate.capabilities),
        supportedPlatforms=list(candidate.supported_platforms),
        provenance=_provenance_response(candidate.provenance),
        version=candidate.version,
        license=candidate.license,
        installationMethod=candidate.installation_method,
        dependencies=list(candidate.dependencies),
        requiredPermissions=list(candidate.required_permissions),
        riskLevel=candidate.risk_level,
        selectionRationale=candidate.selection_rationale,
    )


@router.get("", response_model=list[ToolResponse])
async def list_tools(
    category: ToolCategory | None = None,
    platform: str | None = None,
    trust_status: TrustStatus | None = Query(default=None, alias="trustStatus"),
    search: str | None = None,
    registry: ToolRegistry = Depends(get_tool_registry),
) -> list[ToolResponse]:
    tools = await registry.list(
        category=category, platform=platform, trust_status=trust_status, search=search
    )
    return [_tool_response(t) for t in tools]


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID, registry: ToolRegistry = Depends(get_tool_registry)
) -> ToolResponse:
    try:
        tool = await registry.get(tool_id)
    except ToolRegistryError as exc:
        raise _http_error(exc) from exc
    return _tool_response(tool)


@router.post("/discover", response_model=ToolSelectionProposalResponse)
async def discover_tools(
    request: DiscoverRequest,
    discovery: ToolDiscoveryService = Depends(get_discovery_service),
) -> ToolSelectionProposalResponse:
    candidates = await discovery.discover(request.capability)
    proposal = build_tool_selection_proposal(request.capability, candidates)
    return ToolSelectionProposalResponse(
        requiredCapability=proposal.required_capability,
        reason=proposal.reason,
        expectedPlatforms=list(proposal.expected_platforms),
        expectedDependencies=list(proposal.expected_dependencies),
        verificationRequirements=list(proposal.verification_requirements),
        candidates=[_candidate_response(c) for c in proposal.candidates],
    )


@router.post("", response_model=ToolResponse, status_code=201)
async def register_tool(
    request: RegisterToolRequest, registry: ToolRegistry = Depends(get_tool_registry)
) -> ToolResponse:
    tool = ToolRecord(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        category=request.category,
        capabilities=tuple(request.capabilities),
        supported_platforms=tuple(request.supported_platforms),
        provenance=SourceProvenance(
            source_type=request.source_type,
            source_url=request.source_url,
            repository_url=request.repository_url,
            documentation_url=request.documentation_url,
            publisher=request.publisher,
            discovered_version=request.version,
        ),
        version=request.version,
        license=request.license,
        installation_method=request.installation_method,
        dependencies=tuple(request.dependencies),
        required_permissions=tuple(request.required_permissions),
        risk_level=request.risk_level,
        trust_status=TrustStatus.DISCOVERED,
    )
    try:
        created = await registry.create(tool)
    except ToolRegistryError as exc:
        raise _http_error(exc) from exc
    return _tool_response(created)


@router.post("/{tool_id}/verify", response_model=ToolResponse)
async def verify_tool(
    tool_id: UUID,
    registry: ToolRegistry = Depends(get_tool_registry),
    pipeline: VerificationPipeline = Depends(get_verification_pipeline),
) -> ToolResponse:
    try:
        tool = await registry.get(tool_id)
        report = pipeline.verify(tool)
        tool = await registry.record_verification(tool_id, report)

        overall = report.overall()
        if overall.value == "failed":
            tool = await registry.update_trust_status(tool_id, TrustStatus.BLOCKED)
        elif overall.value == "verified":
            tool = await registry.update_trust_status(tool_id, TrustStatus.VERIFIED)
        else:
            tool = await registry.update_trust_status(tool_id, TrustStatus.UNDER_REVIEW)
    except ToolRegistryError as exc:
        raise _http_error(exc) from exc
    return _tool_response(tool)


@router.post("/{tool_id}/approve", response_model=ToolResponse)
async def approve_tool(
    tool_id: UUID, registry: ToolRegistry = Depends(get_tool_registry)
) -> ToolResponse:
    try:
        tool = await registry.get(tool_id)
        if tool.trust_status != TrustStatus.VERIFIED:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "invalid_trust_transition",
                    "message": f"Tool must be VERIFIED before approval (currently "
                    f"{tool.trust_status.value}).",
                },
            )
        tool = await registry.update_trust_status(tool_id, TrustStatus.APPROVED)
    except ToolRegistryError as exc:
        raise _http_error(exc) from exc
    return _tool_response(tool)


@router.post("/{tool_id}/block", response_model=ToolResponse)
async def block_tool(
    tool_id: UUID, registry: ToolRegistry = Depends(get_tool_registry)
) -> ToolResponse:
    try:
        tool = await registry.update_trust_status(tool_id, TrustStatus.BLOCKED)
    except ToolRegistryError as exc:
        raise _http_error(exc) from exc
    return _tool_response(tool)


@router.post("/{tool_id}/deprecate", response_model=ToolResponse)
async def deprecate_tool(
    tool_id: UUID, registry: ToolRegistry = Depends(get_tool_registry)
) -> ToolResponse:
    try:
        tool = await registry.update_trust_status(tool_id, TrustStatus.DEPRECATED)
    except ToolRegistryError as exc:
        raise _http_error(exc) from exc
    return _tool_response(tool)


@router.get("/{tool_id}/eligibility", response_model=EligibilityResponse)
async def check_eligibility(
    tool_id: UUID,
    platform: str | None = None,
    registry: ToolRegistry = Depends(get_tool_registry),
    gate: ToolPolicyGate = Depends(get_policy_gate),
) -> EligibilityResponse:
    try:
        tool = await registry.get(tool_id)
    except ToolRegistryError as exc:
        raise _http_error(exc) from exc
    decision = gate.evaluate(tool, target_platform=platform)
    return EligibilityResponse(eligible=decision.eligible, reasons=decision.reasons)
