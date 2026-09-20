import pytest
from services.agent_orchestrator.ai_schemas import parse_agent_decision
from services.agent_orchestrator.errors import OutOfScopeError
from services.agent_orchestrator.models import AgentTaskState
from services.agent_orchestrator.policy_gate import AgentPolicyGate

from tests.agent_orchestrator.helpers import decision


def _state(**overrides) -> AgentTaskState:
    defaults = dict(objective="check dns", target="example.test", authorization_status="AUTHORIZED")
    defaults.update(overrides)
    return AgentTaskState(**defaults)


def test_execution_action_requires_authorization():
    gate = AgentPolicyGate()
    state = _state(authorization_status="UNKNOWN")
    d = parse_agent_decision(decision("RUN_DIAGNOSTIC"))
    result = gate.evaluate(state, d)
    assert result.allowed is False


def test_read_only_action_allowed_without_authorization():
    gate = AgentPolicyGate()
    state = _state(authorization_status="UNKNOWN")
    d = parse_agent_decision(decision("CHECK_ENVIRONMENT"))
    result = gate.evaluate(state, d)
    assert result.allowed is True


def test_run_diagnostic_always_requires_approval_even_if_model_says_no():
    gate = AgentPolicyGate()
    state = _state()
    d = parse_agent_decision(decision("RUN_DIAGNOSTIC", requires_approval=False))
    result = gate.evaluate(state, d)
    assert result.requires_approval is True


def test_install_tool_always_requires_approval():
    gate = AgentPolicyGate()
    state = _state()
    d = parse_agent_decision(decision("INSTALL_TOOL", requires_approval=False, tool="dig"))
    result = gate.evaluate(state, d)
    assert result.requires_approval is True


def test_check_environment_does_not_require_approval_by_default():
    gate = AgentPolicyGate()
    state = _state()
    d = parse_agent_decision(decision("CHECK_ENVIRONMENT"))
    result = gate.evaluate(state, d)
    assert result.requires_approval is False


def test_target_outside_scope_raises_out_of_scope():
    gate = AgentPolicyGate()
    state = _state(target="example.test")
    d = parse_agent_decision(
        decision("RUN_DIAGNOSTIC", arguments={"target": "some-other-host.test"})
    )
    with pytest.raises(OutOfScopeError):
        gate.evaluate(state, d)


def test_matching_target_is_within_scope():
    gate = AgentPolicyGate()
    state = _state(target="example.test")
    d = parse_agent_decision(decision("RUN_DIAGNOSTIC", arguments={"target": "Example.Test"}))
    result = gate.evaluate(state, d)
    assert result.allowed is True


def test_build_action_reflects_gate_decision():
    gate = AgentPolicyGate()
    state = _state()
    d = parse_agent_decision(decision("RUN_DIAGNOSTIC", requires_approval=False))
    result = gate.evaluate(state, d)
    action = gate.build_action(d, result)
    assert action.requires_approval is True
    assert action.approval_state.value == "PENDING"
