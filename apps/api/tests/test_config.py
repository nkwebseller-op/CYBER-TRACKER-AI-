import pytest

from app.core.config import ConfigurationError, Settings


def test_mock_provider_allowed_in_development():
    settings = Settings(environment="development", ai_provider="mock")
    assert settings.ai_provider == "mock"


def test_mock_provider_rejected_in_production():
    with pytest.raises(ConfigurationError):
        Settings(environment="production", ai_provider="mock")


def test_unknown_provider_rejected():
    with pytest.raises(ConfigurationError):
        Settings(ai_provider="not-a-real-provider")


def test_gemini_allowed_in_production():
    settings = Settings(environment="production", ai_provider="gemini", gemini_api_key="key")
    assert settings.ai_provider == "gemini"
