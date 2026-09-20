"""ToolDiscoveryService: turns a capability requirement into structured,
never-directly-executable candidates.

    "Need a tool for DNS diagnostics"
          |
    ToolDiscoveryService.discover(capability)
          |
    ToolResearchProvider.search(capability)   (services/tools/research.py)
          |
    [cache / throttle]
          |
    list[ToolCandidate]

Caching and throttling exist so a chatty caller (or an AI proposing
several capabilities in a row) can't turn this into uncontrolled crawling
of an external source once a real research provider is added — the cache
is keyed by the normalized capability string and expires after
`cache_ttl_seconds`; a minimum interval between *provider calls* (not
cached hits) is enforced by `min_seconds_between_provider_calls`.
"""

import asyncio
import time
from dataclasses import dataclass

from services.terminal.audit import AuditEvent, AuditSink, LoggingAuditSink
from services.tools.audit_events import TOOL_DISCOVERED
from services.tools.models import ToolCandidate
from services.tools.research import ToolResearchProvider


@dataclass
class _CacheEntry:
    candidates: list[ToolCandidate]
    expires_at: float


@dataclass
class ToolDiscoveryConfig:
    cache_ttl_seconds: float = 300.0
    min_seconds_between_provider_calls: float = 1.0


class ToolDiscoveryService:
    def __init__(
        self,
        provider: ToolResearchProvider,
        *,
        config: ToolDiscoveryConfig | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._provider = provider
        self._config = config or ToolDiscoveryConfig()
        self._audit = audit_sink or LoggingAuditSink()
        self._cache: dict[str, _CacheEntry] = {}
        self._last_provider_call_at: float = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def _normalize(capability: str) -> str:
        return " ".join(capability.strip().lower().split())

    async def discover(self, capability: str) -> list[ToolCandidate]:
        key = self._normalize(capability)
        if not key:
            return []

        cached = self._cache.get(key)
        now = time.monotonic()
        if cached is not None and cached.expires_at > now:
            return cached.candidates

        async with self._lock:
            # Re-check after acquiring the lock — another caller may have
            # just populated the cache for this exact capability.
            cached = self._cache.get(key)
            now = time.monotonic()
            if cached is not None and cached.expires_at > now:
                return cached.candidates

            wait = self._min_wait_seconds(now)
            if wait > 0:
                await asyncio.sleep(wait)

            candidates = await self._provider.search(capability)
            self._last_provider_call_at = time.monotonic()
            self._cache[key] = _CacheEntry(
                candidates=candidates,
                expires_at=self._last_provider_call_at + self._config.cache_ttl_seconds,
            )

        for candidate in candidates:
            self._audit.emit(
                AuditEvent(
                    event_type=TOOL_DISCOVERED,
                    session_id=None,
                    command_id=None,
                    task_id=None,
                    data={
                        "candidate_name": candidate.name,
                        "capability_requested": capability,
                        "source_type": candidate.provenance.source_type.value,
                    },
                )
            )
        return candidates

    def _min_wait_seconds(self, now: float) -> float:
        elapsed = now - self._last_provider_call_at
        remaining = self._config.min_seconds_between_provider_calls - elapsed
        return max(0.0, remaining)

    def clear_cache(self) -> None:
        self._cache.clear()
