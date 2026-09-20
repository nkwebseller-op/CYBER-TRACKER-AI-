"""Voice control architecture.

    microphone -> SpeechToTextProvider.transcribe -> the SAME
    AgentOrchestrator used by text chat -> policy/authorization/execution
    (unchanged) -> result text -> TextToSpeechProvider.synthesize

There is no separate "voice agent brain" — a transcribed utterance
becomes an ordinary objective/clarification handed to
`AgentOrchestrator.create_task` / `.provide_clarification`, exactly like
typed text. Nothing here bypasses policy, authorization, or approval: a
voice command that would require approval as text still requires it as
voice (see services/agent_orchestrator/orchestrator.py — it has no
"voice" code path at all, only text in and text out).

This phase ships the provider abstraction and session/state machine only
— no real STT/TTS vendor is wired in, matching the phase's "add the
architecture" scope. `NullVoiceProvider` (below) is the safe default;
swapping in a real provider means adding one class here, nothing else in
the orchestrator changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class VoiceState(StrEnum):
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"
    IDLE = "IDLE"


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    is_final: bool


class SpeechToTextProvider(ABC):
    name: str

    @abstractmethod
    async def transcribe(self, audio_chunk: bytes) -> TranscriptionResult:
        """Transcribes one chunk of audio. A real provider would stream;
        this contract stays chunk-based so a batching or streaming
        implementation can both satisfy it."""


class TextToSpeechProvider(ABC):
    name: str

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Returns audio bytes for `text`. Never receives anything but
        the same operational-summary text already shown in the UI — no
        hidden reasoning is ever spoken."""


class NullSpeechToTextProvider(SpeechToTextProvider):
    """Safe default: never silently invents a transcription."""

    name = "null"

    async def transcribe(self, audio_chunk: bytes) -> TranscriptionResult:
        return TranscriptionResult(text="", confidence=0.0, is_final=True)


class NullTextToSpeechProvider(TextToSpeechProvider):
    name = "null"

    async def synthesize(self, text: str) -> bytes:
        return b""


@dataclass
class VoiceSession:
    id: UUID = field(default_factory=uuid4)
    task_id: UUID | None = None
    state: VoiceState = VoiceState.IDLE
    last_transcript: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)


class VoiceSessionManager:
    """Drives the LISTENING -> THINKING -> EXECUTING -> SPEAKING state
    machine. Text fallback is always available: any state can transition
    directly to IDLE via `cancel()`, and nothing here calls the
    orchestrator itself — that wiring belongs to the API layer, which
    already knows how to call AgentOrchestrator for text."""

    def __init__(
        self,
        *,
        stt: SpeechToTextProvider | None = None,
        tts: TextToSpeechProvider | None = None,
    ) -> None:
        self._stt = stt or NullSpeechToTextProvider()
        self._tts = tts or NullTextToSpeechProvider()
        self._sessions: dict[UUID, VoiceSession] = {}

    def start_listening(self, task_id: UUID | None = None) -> VoiceSession:
        session = VoiceSession(task_id=task_id, state=VoiceState.LISTENING)
        self._sessions[session.id] = session
        return session

    def stop_listening(self, session_id: UUID) -> VoiceSession:
        session = self._require(session_id)
        session.state = VoiceState.THINKING
        session.touch()
        return session

    def mark_executing(self, session_id: UUID) -> VoiceSession:
        session = self._require(session_id)
        session.state = VoiceState.EXECUTING
        session.touch()
        return session

    def mark_speaking(self, session_id: UUID) -> VoiceSession:
        session = self._require(session_id)
        session.state = VoiceState.SPEAKING
        session.touch()
        return session

    def interrupt(self, session_id: UUID) -> VoiceSession:
        session = self._require(session_id)
        session.state = VoiceState.INTERRUPTED
        session.touch()
        return session

    def cancel(self, session_id: UUID) -> VoiceSession:
        session = self._require(session_id)
        session.state = VoiceState.IDLE
        session.touch()
        return session

    def mark_error(self, session_id: UUID) -> VoiceSession:
        session = self._require(session_id)
        session.state = VoiceState.ERROR
        session.touch()
        return session

    async def transcribe(self, session_id: UUID, audio_chunk: bytes) -> TranscriptionResult:
        session = self._require(session_id)
        result = await self._stt.transcribe(audio_chunk)
        session.last_transcript = result.text
        session.touch()
        return result

    async def speak(self, session_id: UUID, text: str) -> bytes:
        self.mark_speaking(session_id)
        return await self._tts.synthesize(text)

    def _require(self, session_id: UUID) -> VoiceSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Voice session {session_id} does not exist.")
        return session
