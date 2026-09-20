import pytest
from services.agent.schemas import AIResponseValidationError, parse_ai_response

from tests.fakes import valid_ai_response_payload


def test_parse_ai_response_accepts_valid_payload():
    response = parse_ai_response(valid_ai_response_payload())
    assert response.task_intent.objective == "Test objective"
    assert response.task_plan.workflow[0].key.value == "UNDERSTAND"


def test_parse_ai_response_rejects_missing_required_field():
    payload = valid_ai_response_payload()
    del payload["taskIntent"]

    with pytest.raises(AIResponseValidationError):
        parse_ai_response(payload)


def test_parse_ai_response_rejects_invalid_enum_value():
    payload = valid_ai_response_payload()
    payload["riskLevel"] = "EXTREME"

    with pytest.raises(AIResponseValidationError):
        parse_ai_response(payload)


def test_parse_ai_response_rejects_non_dict():
    with pytest.raises(AIResponseValidationError):
        parse_ai_response({"message": "only a message, nothing else"})
