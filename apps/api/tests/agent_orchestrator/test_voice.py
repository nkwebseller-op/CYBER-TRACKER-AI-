from services.agent_orchestrator.voice import (
    NullSpeechToTextProvider,
    NullTextToSpeechProvider,
    VoiceSessionManager,
    VoiceState,
)


async def test_start_listening_sets_state():
    manager = VoiceSessionManager()
    session = manager.start_listening()
    assert session.state == VoiceState.LISTENING


async def test_stop_listening_transitions_to_thinking():
    manager = VoiceSessionManager()
    session = manager.start_listening()
    updated = manager.stop_listening(session.id)
    assert updated.state == VoiceState.THINKING


async def test_interrupt_sets_interrupted_state():
    manager = VoiceSessionManager()
    session = manager.start_listening()
    updated = manager.interrupt(session.id)
    assert updated.state == VoiceState.INTERRUPTED


async def test_cancel_returns_to_idle_text_fallback():
    manager = VoiceSessionManager()
    session = manager.start_listening()
    updated = manager.cancel(session.id)
    assert updated.state == VoiceState.IDLE


async def test_null_stt_never_fabricates_a_transcription():
    provider = NullSpeechToTextProvider()
    result = await provider.transcribe(b"audio-bytes")
    assert result.text == ""
    assert result.confidence == 0.0


async def test_null_tts_returns_empty_audio():
    provider = NullTextToSpeechProvider()
    audio = await provider.synthesize("hello")
    assert audio == b""


async def test_transcribe_updates_session_transcript():
    manager = VoiceSessionManager()
    session = manager.start_listening()
    await manager.transcribe(session.id, b"chunk")
    # Null provider produces empty transcript, but the session must still
    # record whatever was returned (never invent something else).
    assert manager._sessions[session.id].last_transcript == ""  # noqa: SLF001


async def test_speak_transitions_to_speaking_state():
    manager = VoiceSessionManager()
    session = manager.start_listening()
    await manager.speak(session.id, "task completed")
    assert manager._sessions[session.id].state == VoiceState.SPEAKING  # noqa: SLF001


async def test_unknown_session_raises():
    import pytest

    manager = VoiceSessionManager()
    with pytest.raises(KeyError):
        manager.stop_listening(__import__("uuid").uuid4())
