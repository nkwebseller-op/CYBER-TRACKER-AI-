from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from .base import ProviderError, ScriptWriter, VideoProvider, VoiceProvider
from .cards_video import CardsVideo
from .elevenlabs import ElevenLabsVoice
from .mock_voice import MockVoice
from .template_script import TemplateScriptWriter

__all__ = ["ProviderError", "Providers", "build_providers"]


@dataclass(frozen=True)
class Providers:
    script: ScriptWriter
    voice: VoiceProvider
    video: VideoProvider


def build_providers(settings: Settings) -> Providers:
    if settings.script_provider != "template":
        raise ProviderError(f"Unknown SCRIPT_PROVIDER {settings.script_provider!r}")
    voice: VoiceProvider
    if settings.voice_provider == "mock":
        voice = MockVoice(settings.ffmpeg_bin)
    elif settings.voice_provider == "elevenlabs":
        voice = ElevenLabsVoice(
            settings.elevenlabs_api_key, settings.elevenlabs_voice_id, settings.elevenlabs_model
        )
    else:
        raise ProviderError(f"Unknown VOICE_PROVIDER {settings.voice_provider!r}")
    if settings.video_provider != "cards":
        raise ProviderError(f"Unknown VIDEO_PROVIDER {settings.video_provider!r}")
    return Providers(
        script=TemplateScriptWriter(),
        voice=voice,
        video=CardsVideo(settings.ffmpeg_bin, settings.ffprobe_bin, settings.font_file),
    )
