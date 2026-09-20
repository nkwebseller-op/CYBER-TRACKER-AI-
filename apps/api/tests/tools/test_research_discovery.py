import asyncio

from services.tools.discovery import ToolDiscoveryConfig, ToolDiscoveryService
from services.tools.models import SourceProvenance, SourceType, ToolCandidate
from services.tools.research import CuratedToolResearchProvider

from tests.terminal.helpers import RecordingAuditSink


class FakeProvider:
    def __init__(self, candidates: list[ToolCandidate]) -> None:
        self.candidates = candidates
        self.calls: list[str] = []

    async def search(self, capability: str) -> list[ToolCandidate]:
        self.calls.append(capability)
        return self.candidates


def _candidate(name="dig") -> ToolCandidate:
    return ToolCandidate(
        name=name,
        display_name=name,
        description="test tool",
        provenance=SourceProvenance(source_type=SourceType.OFFICIAL_WEBSITE),
    )


async def test_curated_provider_matches_dns_capability():
    provider = CuratedToolResearchProvider()
    results = await provider.search("dns diagnostics")
    assert any(c.name == "dig" for c in results)


async def test_curated_provider_returns_empty_for_unrelated_capability():
    provider = CuratedToolResearchProvider()
    results = await provider.search("underwater basket weaving")
    assert results == []


async def test_discovery_service_returns_candidates_from_provider():
    provider = FakeProvider([_candidate()])
    service = ToolDiscoveryService(provider)

    results = await service.discover("dns")
    assert [c.name for c in results] == ["dig"]
    assert provider.calls == ["dns"]


async def test_discovery_service_caches_repeat_requests():
    provider = FakeProvider([_candidate()])
    service = ToolDiscoveryService(provider, config=ToolDiscoveryConfig(cache_ttl_seconds=60))

    await service.discover("dns")
    await service.discover("dns")

    assert provider.calls == ["dns"]  # second call served from cache


async def test_discovery_service_normalizes_capability_for_cache_key():
    provider = FakeProvider([_candidate()])
    service = ToolDiscoveryService(provider)

    await service.discover("  DNS  ")
    await service.discover("dns")

    assert provider.calls == ["  DNS  "]


async def test_discovery_service_emits_audit_event_per_candidate():
    provider = FakeProvider([_candidate("dig"), _candidate("nslookup")])
    sink = RecordingAuditSink()
    service = ToolDiscoveryService(provider, audit_sink=sink)

    await service.discover("dns")

    assert sink.event_types.count("tool.discovered") == 2


async def test_discovery_service_returns_empty_for_blank_capability():
    provider = FakeProvider([_candidate()])
    service = ToolDiscoveryService(provider)

    results = await service.discover("   ")
    assert results == []
    assert provider.calls == []


async def test_discovery_service_throttles_provider_calls():
    provider = FakeProvider([_candidate()])
    config = ToolDiscoveryConfig(cache_ttl_seconds=0, min_seconds_between_provider_calls=0.2)
    service = ToolDiscoveryService(provider, config=config)

    start = asyncio.get_event_loop().time()
    await service.discover("dns")
    await service.discover("network")  # different key, but throttled by min interval
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed >= 0.15
