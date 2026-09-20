import pytest
from services.tools.errors import DuplicateToolError, ToolNotFoundError
from services.tools.models import ToolCategory, ToolRecord, TrustStatus
from services.tools.registry import InMemoryToolRegistry


def _tool(name="dig", **overrides) -> ToolRecord:
    defaults = dict(
        name=name,
        display_name=name,
        description="DNS lookup tool",
        category=ToolCategory.DNS_DOMAIN_ANALYSIS,
        capabilities=("dns_lookup",),
        supported_platforms=("LINUX", "MACOS"),
    )
    defaults.update(overrides)
    return ToolRecord(**defaults)


async def test_create_and_get_tool():
    registry = InMemoryToolRegistry()
    created = await registry.create(_tool())

    fetched = await registry.get(created.id)
    assert fetched.name == "dig"


async def test_get_unknown_tool_raises():
    registry = InMemoryToolRegistry()
    with pytest.raises(ToolNotFoundError):
        await registry.get(__import__("uuid").uuid4())


async def test_duplicate_name_is_rejected():
    registry = InMemoryToolRegistry()
    await registry.create(_tool())
    with pytest.raises(DuplicateToolError):
        await registry.create(_tool())


async def test_get_by_name_returns_none_when_absent():
    registry = InMemoryToolRegistry()
    assert await registry.get_by_name("nope") is None


async def test_list_filters_by_category():
    registry = InMemoryToolRegistry()
    await registry.create(_tool(name="dig", category=ToolCategory.DNS_DOMAIN_ANALYSIS))
    await registry.create(_tool(name="nmap", category=ToolCategory.NETWORK_DIAGNOSTICS))

    results = await registry.list(category=ToolCategory.NETWORK_DIAGNOSTICS)
    assert [t.name for t in results] == ["nmap"]


async def test_list_filters_by_platform():
    registry = InMemoryToolRegistry()
    await registry.create(_tool(name="dig", supported_platforms=("LINUX",)))
    await registry.create(_tool(name="pwsh-tool", supported_platforms=("WINDOWS",)))

    results = await registry.list(platform="WINDOWS")
    assert [t.name for t in results] == ["pwsh-tool"]


async def test_list_filters_by_trust_status():
    registry = InMemoryToolRegistry()
    t1 = await registry.create(_tool(name="dig"))
    await registry.create(_tool(name="nmap"))
    await registry.update_trust_status(t1.id, TrustStatus.APPROVED)

    results = await registry.list(trust_status=TrustStatus.APPROVED)
    assert [t.name for t in results] == ["dig"]


async def test_list_search_matches_name_and_capability():
    registry = InMemoryToolRegistry()
    await registry.create(_tool(name="dig", capabilities=("dns_lookup",)))
    await registry.create(_tool(name="nmap", capabilities=("port_scan",)))

    results = await registry.list(search="dns_lookup")
    assert [t.name for t in results] == ["dig"]


async def test_update_trust_status_persists():
    registry = InMemoryToolRegistry()
    tool = await registry.create(_tool())
    updated = await registry.update_trust_status(tool.id, TrustStatus.VERIFIED)
    assert updated.trust_status == TrustStatus.VERIFIED
    refetched = await registry.get(tool.id)
    assert refetched.trust_status == TrustStatus.VERIFIED
