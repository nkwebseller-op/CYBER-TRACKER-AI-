from uuid import uuid4

import pytest
from services.installation.config import InstallationServiceConfig
from services.installation.environment import EnvironmentInspector
from services.installation.errors import ApprovalRequiredError, InvalidStateTransitionError
from services.installation.models import InstallationState, PackageManager
from services.installation.registry import InMemoryInstallationRegistry
from services.installation.service import ToolInstallationService
from services.policy.engine import RiskTier, TargetScope
from services.terminal.adapters.base import ExecutionResult, ExecutionStatus
from services.terminal.audit import AuditEvent, AuditSink
from services.terminal.engine import TerminalEngine
from services.tools.registry import InMemoryToolRegistry

from tests.installation.helpers import (
    ScriptedAdapter,
    approved_tool,
    failure_result,
    success_result,
)


class RecordingSink(AuditSink):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    @property
    def event_types(self) -> list[str]:
        return [e.event_type for e in self.events]


class FixedEnvironment(EnvironmentInspector):
    def inspect(self, *, identifier=None):
        from services.installation.models import EnvironmentCheck

        return EnvironmentCheck(
            platform="LINUX",
            architecture="x86_64",
            shell="/bin/bash",
            available_package_managers=(PackageManager.APT,),
        )


def _service(adapter, *, audit_sink=None, max_attempts=2):
    tools = InMemoryToolRegistry()
    installations = InMemoryInstallationRegistry()
    engine = TerminalEngine(adapter=adapter)
    service = ToolInstallationService(
        tools=tools,
        installations=installations,
        environment_inspector=FixedEnvironment(),
        config=InstallationServiceConfig(max_install_attempts=max_attempts),
        audit_sink=audit_sink,
    )
    return service, tools, engine


ACTIVE_TARGET = TargetScope(id=uuid4(), is_active=True, expires_at=None)
INACTIVE_TARGET = TargetScope(id=uuid4(), is_active=False, expires_at=None)


async def test_happy_path_reaches_installed():
    adapter = ScriptedAdapter([success_result("installed ok"), success_result("dig 9.18")])
    service, tools, engine = _service(adapter)
    tool = await tools.create(approved_tool())

    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert request.state == InstallationState.WAITING_FOR_APPROVAL

    approved = await service.approve(request.id, approved_by="ops@example.com")
    assert approved.state == InstallationState.PREPARING

    session = engine.create_session()
    finished = await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )
    assert finished.state == InstallationState.INSTALLED
    assert finished.verification.verified is True
    assert len(finished.attempts) == 1


async def test_tool_not_approved_is_blocked_at_request_time():
    from services.tools.models import TrustStatus

    adapter = ScriptedAdapter([])
    service, tools, _engine = _service(adapter)
    tool = await tools.create(approved_tool(trust_status=TrustStatus.DISCOVERED))

    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert request.state == InstallationState.BLOCKED
    assert adapter.calls == []


async def test_unsupported_platform_is_blocked_at_request_time():
    adapter = ScriptedAdapter([])
    service, tools, _engine = _service(adapter)
    tool = await tools.create(approved_tool(supported_platforms=("WINDOWS",)))

    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert request.state == InstallationState.BLOCKED


async def test_authorization_rejection_blocks_before_any_execution():
    adapter = ScriptedAdapter([])
    service, tools, _engine = _service(adapter)
    tool = await tools.create(approved_tool())

    request = await service.request_installation(
        tool.id, target_scope=INACTIVE_TARGET, platform="LINUX"
    )
    assert request.state == InstallationState.BLOCKED
    assert adapter.calls == []


async def test_start_before_approval_raises():
    adapter = ScriptedAdapter([])
    service, tools, engine = _service(adapter)
    tool = await tools.create(approved_tool())
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )

    session = engine.create_session()
    with pytest.raises(ApprovalRequiredError):
        await service.start_installation(
            request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
        )


async def test_low_risk_tool_skips_approval():
    adapter = ScriptedAdapter([success_result(), success_result("dig 9.18")])
    service, tools, engine = _service(adapter)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))

    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    assert request.state == InstallationState.PREPARING

    session = engine.create_session()
    finished = await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )
    assert finished.state == InstallationState.INSTALLED


async def test_reject_marks_cancelled():
    adapter = ScriptedAdapter([])
    service, tools, _engine = _service(adapter)
    tool = await tools.create(approved_tool())
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )

    rejected = await service.reject(request.id, reason="Not needed right now.")
    assert rejected.state == InstallationState.CANCELLED
    assert rejected.rejection_reason == "Not needed right now."


async def test_cancel_while_waiting_for_approval_is_immediate():
    adapter = ScriptedAdapter([])
    service, tools, engine = _service(adapter)
    tool = await tools.create(approved_tool())
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )

    cancelled = await service.cancel(request.id, engine)
    assert cancelled.state == InstallationState.CANCELLED


async def test_cancel_after_terminal_state_is_a_no_op():
    adapter = ScriptedAdapter([])
    service, tools, engine = _service(adapter)
    tool = await tools.create(approved_tool())
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    await service.reject(request.id, reason="no")

    result = await service.cancel(request.id, engine)
    assert result.state == InstallationState.CANCELLED  # unchanged, no error


async def test_installation_failure_after_exhausting_retries():
    adapter = ScriptedAdapter(
        [failure_result("network unreachable"), failure_result("network unreachable 2")]
    )
    service, tools, engine = _service(adapter, max_attempts=2)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    session = engine.create_session()
    finished = await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )
    assert finished.state == InstallationState.FAILED
    assert len(finished.attempts) == 2


async def test_loop_detection_stops_before_exhausting_all_attempts():
    """Both failures share the same error category (FAILED) — loop
    detection should stop after the second identical failure even though
    max_install_attempts allows a third."""
    adapter = ScriptedAdapter([failure_result(), failure_result(), failure_result()])
    service, tools, engine = _service(adapter, max_attempts=5)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    session = engine.create_session()
    finished = await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )
    assert finished.state == InstallationState.FAILED
    assert len(finished.attempts) == 2  # stopped early, not all 5


async def test_verification_failure_marks_rollback_required():
    # second result simulates a verify command that ran but produced no output
    adapter = ScriptedAdapter([success_result("install ok"), success_result("")])
    service, tools, engine = _service(adapter, max_attempts=1)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    session = engine.create_session()
    finished = await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )
    assert finished.state == InstallationState.ROLLBACK_REQUIRED
    assert finished.verification.verified is False


async def test_timeout_result_marks_failed_not_installed():
    timeout_result = ExecutionResult(
        adapter="scripted", status=ExecutionStatus.FAILED, timed_out=True, stderr="timed out"
    )
    adapter = ScriptedAdapter([timeout_result])
    service, tools, engine = _service(adapter, max_attempts=1)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    session = engine.create_session()
    finished = await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )
    # A timeout is a distinct, non-retried-forever failure category.
    assert finished.state == InstallationState.FAILED
    assert finished.attempts[0].error_category == "TIMEOUT"


async def test_audit_events_cover_full_lifecycle():
    sink = RecordingSink()
    adapter = ScriptedAdapter([success_result(), success_result("dig 9.18")])
    service, tools, engine = _service(adapter, audit_sink=sink)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))

    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    session = engine.create_session()
    await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )

    assert "install.requested" in sink.event_types
    assert "install.readiness_checked" in sink.event_types
    assert "install.plan_generated" in sink.event_types
    assert "install.started" in sink.event_types
    assert "install.step_completed" in sink.event_types
    assert "install.verified" in sink.event_types
    assert "install.completed" in sink.event_types


async def test_audit_events_never_include_secret_like_values():
    sink = RecordingSink()
    adapter = ScriptedAdapter([success_result(), success_result("dig 9.18")])
    service, tools, engine = _service(adapter, audit_sink=sink)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))

    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    session = engine.create_session()
    await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )

    for event in sink.events:
        serialized = str(event.data).lower()
        assert "api_key" not in serialized
        assert "password" not in serialized
        assert "secret" not in serialized


async def test_approve_on_wrong_state_raises():
    adapter = ScriptedAdapter([success_result(), success_result()])
    service, tools, _engine = _service(adapter)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )  # already PREPARING (low risk, no approval needed)

    with pytest.raises(InvalidStateTransitionError):
        await service.approve(request.id, approved_by="ops@example.com")


async def test_installation_request_never_carries_environment_secrets():
    """The install/verify TerminalCommandRequest never sets `environment`
    — nothing from the server's own process environment is ever attached
    to an install command by this service."""
    adapter = ScriptedAdapter([success_result(), success_result("dig 9.18")])
    service, tools, engine = _service(adapter, max_attempts=1)
    tool = await tools.create(approved_tool(risk_level=RiskTier.LOW))
    request = await service.request_installation(
        tool.id, target_scope=ACTIVE_TARGET, platform="LINUX"
    )
    session = engine.create_session()
    await service.start_installation(
        request.id, engine=engine, session_id=session.id, target_scope=ACTIVE_TARGET
    )
    for spec in adapter.calls:
        assert spec.env_overrides == {}
