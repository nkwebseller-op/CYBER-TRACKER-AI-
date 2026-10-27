
from studio.providers.template_script import TemplateScriptWriter


async def test_template_script_has_hook_points_and_cta():
    script = await TemplateScriptWriter().write("Fast setup. Cheap plans. Great support.", "friendly", 30)
    captions = [s.caption for s in script.scenes]
    assert captions[0] == "Hey, quick question for you."
    assert captions[1:4] == ["Fast setup", "Cheap plans", "Great support"]
    assert captions[-1] == "Give it a try, you will love it."


async def test_template_script_respects_duration_budget():
    brief = ". ".join(f"Point number {i} has several words in it" for i in range(30)) + "."
    script = await TemplateScriptWriter().write(brief, "energetic", 10)
    assert len(script.narration.split()) <= 10 * 2.5 + 10




def test_build_providers_requires_credentials_for_real_providers(settings):
    import dataclasses

    import pytest

    from studio.providers import ProviderError, build_providers

    with pytest.raises(ProviderError, match="REPLICATE_API_TOKEN"):
        build_providers(dataclasses.replace(settings, video_provider="replicate"))
    with pytest.raises(ProviderError, match="ELEVENLABS_API_KEY"):
        build_providers(dataclasses.replace(settings, voice_provider="elevenlabs"))
    with pytest.raises(ProviderError, match="not valid JSON"):
        build_providers(
            dataclasses.replace(
                settings, video_provider="replicate", replicate_api_token="t", replicate_video_input="{"
            )
        )
