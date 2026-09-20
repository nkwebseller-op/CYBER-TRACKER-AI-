from services.agent.prompts import SYSTEM_INSTRUCTION, build_user_message_block
from services.agent.providers.base import Message, ProviderHealthStatus
from services.agent.providers.mock import MockProvider
from services.agent.schemas import parse_ai_response


async def test_mock_provider_generates_valid_structured_response():
    provider = MockProvider()
    messages = [
        Message(role="system", content=SYSTEM_INSTRUCTION),
        Message(
            role="user",
            content=build_user_message_block("Analyze my authorized web application."),
        ),
    ]

    result = await provider.generate_structured(messages, schema={})
    ai_response = parse_ai_response(result.data)

    assert ai_response.task_intent.objective == "Analyze my authorized web application."
    assert ai_response.task_intent.target_type.value == "web_application"
    assert ai_response.task_intent.authorization_status.value == "UNKNOWN"


async def test_mock_provider_reports_missing_target_when_absent():
    provider = MockProvider()
    content = build_user_message_block("Check my website for issues.")
    messages = [Message(role="user", content=content)]

    result = await provider.generate_structured(messages, schema={})
    ai_response = parse_ai_response(result.data)

    assert "target" in [f.value for f in ai_response.task_intent.missing_information]
    assert "authorization" in [f.value for f in ai_response.task_intent.missing_information]


async def test_mock_provider_health_check_is_always_connected():
    health = await MockProvider().health_check()
    assert health.status == ProviderHealthStatus.CONNECTED
