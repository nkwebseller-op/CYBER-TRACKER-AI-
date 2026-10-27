from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import Settings
from .base import ProviderError, ScriptWriter, VideoProvider, VoiceProvider
from .cards_video import CardsVideo
from .elevenlabs import ElevenLabsVoice
from .mock_voice import MockVoice
from .replicate_video import ReplicateVideo
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
    video: VideoProvider
    if settings.video_provider == "cards":
        video = CardsVideo(settings.ffmpeg_bin, settings.ffprobe_bin, settings.font_file)
    elif settings.video_provider == "replicate":
        try:
            extra = json.loads(settings.replicate_video_input or "{}")
        except json.JSONDecodeError as exc:
            raise ProviderError("REPLICATE_VIDEO_INPUT is not valid JSON") from exc
        if not isinstance(extra, dict):
            raise ProviderError("REPLICATE_VIDEO_INPUT must be a JSON object")
        video = ReplicateVideo(
            token=settings.replicate_api_token,
            model=settings.replicate_video_model,
            extra_input=extra,
            clip_seconds=settings.replicate_clip_seconds,
            timeout_s=settings.replicate_timeout_seconds,
            max_clips=settings.replicate_max_clips,
            ffmpeg_bin=settings.ffmpeg_bin,
            ffprobe_bin=settings.ffprobe_bin,
            font_file=settings.font_file,
        )
    else:
        raise ProviderError(f"Unknown VIDEO_PROVIDER {settings.video_provider!r}")
    return Providers(script=TemplateScriptWriter(), voice=voice, video=video)
