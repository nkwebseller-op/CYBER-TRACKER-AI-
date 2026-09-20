"""AI provider abstraction.

No other module in the codebase should import a model SDK directly (e.g.
`google.genai`). Everything that needs a completion depends on `AIProvider`,
constructed via `get_provider()`. Adding a new provider means adding one
file here and one branch in `get_provider` — nothing else in the
orchestrator, chat pipeline, or API routes changes.

Phase 4 adds `generate_structured` (JSON-schema-constrained output, used by
the Chat API to produce TaskIntent/TaskPlan data) and `health_check`
(used by the AI provider health endpoint and the frontend status pill).
`complete`/`stream` remain for free-form completions.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum


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


@dataclass
class StructuredCompletionResult:
    data: dict
    raw_text: str
    model: str
    provider: str


class AIProviderErrorCode(StrEnum):
    MISSING_API_KEY = "missing_api_key"
    INVALID_API_KEY = "invalid_api_key"
    CONFIGURATION_ERROR = "configuration_error"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    NETWORK_ERROR = "network_error"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


# Errors worth a bounded retry: transient network/availability conditions.
# Never retried: bad credentials, bad requests, or our own validation
# failures — retrying those just wastes calls and hides a real problem.
RETRYABLE_ERROR_CODES = frozenset(
    {
        AIProviderErrorCode.UNAVAILABLE,
        AIProviderErrorCode.TIMEOUT,
        AIProviderErrorCode.NETWORK_ERROR,
        AIProviderErrorCode.RATE_LIMITED,
    }
)


class AIProviderError(RuntimeError):
    """Raised when a provider call fails (network, auth, quota, etc.).

    `message` is always safe to show to a user or put in a log line — never
    put the API key, an Authorization header, or a raw SDK exception's
    string form here if it might contain either.
    """

    def __init__(
        self, message: str, *, code: AIProviderErrorCode = AIProviderErrorCode.UNKNOWN
    ) -> None:
        super().__init__(message)
        self.code = code

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE_ERROR_CODES


class ProviderHealthStatus(StrEnum):
    CONNECTED = "connected"
    NOT_CONFIGURED = "not_configured"
    CONFIGURATION_ERROR = "configuration_error"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderHealth:
    provider: str
    status: ProviderHealthStatus
    model: str | None = None
    detail: str | None = None  # safe, user-facing text only — never a secret


class AIProvider(ABC):
    """Contract every AI backend must satisfy."""

    name: str

    @abstractmethod
    async def complete(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> CompletionResult:
        """Return a single free-form completion for the given conversation."""

    @abstractmethod
    async def stream(
        self, messages: list[Message], *, temperature: float = 0.2
    ) -> AsyncIterator[str]:
        """Yield incremental text chunks for the given conversation."""

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[Message],
        *,
        schema: dict,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> StructuredCompletionResult:
        """Return a completion constrained to the given JSON schema.

        Implementations must raise AIProviderError(code=INVALID_RESPONSE)
        rather than returning malformed data — callers must be able to
        trust that a successful return is valid JSON matching `schema` at
        the structural level (full semantic validation still happens in
        services/agent/schemas.py on the caller's side).
        """

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Cheaply verify configuration/connectivity without generating a
        full completion (e.g. a metadata call), distinguishing a
        configuration problem from a transient availability problem where
        possible."""
