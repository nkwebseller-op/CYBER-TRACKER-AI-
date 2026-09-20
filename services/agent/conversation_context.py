"""Bounded conversation-context construction for the chat pipeline.

The provider only ever receives what it needs for the current turn: a
capped number of recent messages (each length-capped too) plus a short,
application-computed summary of known state (existing task intent,
target/authorization info if any, user constraints). It never receives
unlimited history — see MAX_HISTORY_MESSAGES / MAX_MESSAGE_CHARS below.
"""

from dataclasses import dataclass, field

from services.agent.providers.base import Message

MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_CHARS = 2000
MAX_TOTAL_CONTEXT_CHARS = 16000


@dataclass
class ConversationTurn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class ConversationContext:
    conversation_id: str
    history: list[ConversationTurn] = field(default_factory=list)
    known_target: str | None = None
    known_authorization_status: str | None = None
    known_constraints: list[str] = field(default_factory=list)
    existing_objective: str | None = None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def bounded_history(context: ConversationContext) -> list[ConversationTurn]:
    """Most recent MAX_HISTORY_MESSAGES turns, each capped in length, further
    capped so the total never exceeds MAX_TOTAL_CONTEXT_CHARS."""
    recent = context.history[-MAX_HISTORY_MESSAGES:]
    capped = [
        ConversationTurn(role=turn.role, content=_truncate(turn.content, MAX_MESSAGE_CHARS))
        for turn in recent
    ]

    total = 0
    result: list[ConversationTurn] = []
    for turn in reversed(capped):
        total += len(turn.content)
        if total > MAX_TOTAL_CONTEXT_CHARS:
            break
        result.append(turn)
    result.reverse()
    return result


def build_context_summary(context: ConversationContext) -> str:
    lines = [
        f"- Conversation ID: {context.conversation_id}",
        f"- Existing objective: {context.existing_objective or 'none captured yet'}",
        f"- Known target: {context.known_target or 'unknown'}",
        f"- Known authorization status: {context.known_authorization_status or 'UNKNOWN'}",
        f"- User-stated constraints: {', '.join(context.known_constraints) or 'none'}",
    ]
    return "\n".join(lines)


def to_provider_messages(history: list[ConversationTurn]) -> list[Message]:
    return [Message(role=turn.role, content=turn.content) for turn in history]
