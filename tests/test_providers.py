import pytest

from studio.providers.base import ProviderError
from studio.providers.elevenlabs import ElevenLabsVoice
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


def test_elevenlabs_requires_key():
    with pytest.raises(ProviderError):
        ElevenLabsVoice("", "voice", "model")
