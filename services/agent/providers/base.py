"""AI provider abstraction.

No other module in the codebase should import a model SDK directly (e.g.
`google.genai`). Everything that needs a completion depends on `AIProvider`,
constructed via `get_provider()`. Adding a new provider means adding one
file here and one branch in `get_provider` — nothing else in the
orchestrator, planner, or API routes changes.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class CompletionResult:
    text: str
    model: str
    provider: str
    raw: dict = field(default_factory=dict)


class AIProvider(ABC):
    """Contract every AI backend must satisfy."""

    name: str

    @abstractmethod
    async def complete(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> CompletionResult:
        """Return a single completion for the given conversation."""

    @abstractmethod
    async def stream(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        """Yield incremental text chunks for the given conversation."""


class AIProviderError(RuntimeError):
    """Raised when a provider call fails (network, auth, quota, etc.)."""
