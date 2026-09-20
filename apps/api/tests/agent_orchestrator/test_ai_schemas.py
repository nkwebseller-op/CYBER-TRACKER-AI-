import pytest
from services.agent_orchestrator.ai_schemas import (
    AgentDecisionValidationError,
    parse_agent_decision,
)

from tests.agent_orchestrator.helpers import decision


def test_valid_decision_parses():
    parsed = parse_agent_decision(decision("CHECK_ENVIRONMENT"))
    assert parsed.action_type.value == "CHECK_ENVIRONMENT"
    assert parsed.confidence == 0.7


def test_missing_required_field_is_rejected():
    payload = decision("CHECK_ENVIRONMENT")
    del payload["confidence"]
    with pytest.raises(AgentDecisionValidationError):
        parse_agent_decision(payload)


def test_unknown_action_type_is_rejected():
    payload = decision("DELETE_EVERYTHING")
    with pytest.raises(AgentDecisionValidationError):
        parse_agent_decision(payload)


def test_confidence_out_of_range_is_rejected():
    payload = decision("CHECK_ENVIRONMENT", confidence=1.5)
    with pytest.raises(AgentDecisionValidationError):
        parse_agent_decision(payload)


def test_missing_action_type_is_rejected():
    payload = decision("CHECK_ENVIRONMENT")
    del payload["actionType"]
    with pytest.raises(AgentDecisionValidationError):
        parse_agent_decision(payload)


def test_extra_unknown_fields_are_ignored_not_fatal():
    payload = decision("CHECK_ENVIRONMENT")
    payload["somethingUnexpected"] = "ignored"
    parsed = parse_agent_decision(payload)
    assert parsed.action_type.value == "CHECK_ENVIRONMENT"
