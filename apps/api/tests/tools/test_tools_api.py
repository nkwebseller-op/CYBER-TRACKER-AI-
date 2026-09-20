from services.tools.discovery import ToolDiscoveryService
from services.tools.registry import InMemoryToolRegistry
from services.tools.research import CuratedToolResearchProvider

from app.api.routes import tools as tools_routes
from app.core.tools import get_discovery_service, get_tool_registry
from app.main import app


def _override():
    registry = InMemoryToolRegistry()
    discovery = ToolDiscoveryService(CuratedToolResearchProvider())
    app.dependency_overrides[get_tool_registry] = lambda: registry
    app.dependency_overrides[get_discovery_service] = lambda: discovery
    return registry, discovery


def _teardown():
    app.dependency_overrides.pop(get_tool_registry, None)
    app.dependency_overrides.pop(get_discovery_service, None)


async def test_discover_endpoint_returns_candidates(client):
    _override()
    response = await client.post("/api/tools/discover", json={"capability": "dns"})

    assert response.status_code == 200
    body = response.json()
    assert body["requiredCapability"] == "dns"
    assert any(c["name"] == "dig" for c in body["candidates"])
    _teardown()


async def test_register_tool_creates_entry(client):
    _override()
    response = await client.post(
        "/api/tools",
        json={
            "name": "dig",
            "displayName": "dig",
            "description": "DNS lookup tool",
            "category": "dns_domain_analysis",
            "capabilities": ["dns_lookup"],
            "supportedPlatforms": ["LINUX", "MACOS"],
            "sourceType": "official_website",
            "sourceUrl": "https://isc.org",
            "version": "9.18",
            "license": "MPL-2.0",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["trustStatus"] == "discovered"
    assert body["name"] == "dig"
    _teardown()


async def test_register_duplicate_tool_returns_409(client):
    _override()
    payload = {
        "name": "dig",
        "displayName": "dig",
        "description": "DNS lookup tool",
        "category": "dns_domain_analysis",
        "sourceType": "official_website",
    }
    await client.post("/api/tools", json=payload)
    response = await client.post("/api/tools", json=payload)

    assert response.status_code == 409
    _teardown()


async def test_get_unknown_tool_returns_404(client):
    _override()
    from uuid import uuid4

    response = await client.get(f"/api/tools/{uuid4()}")
    assert response.status_code == 404
    _teardown()


async def test_full_verify_and_approve_flow(client):
    _override()
    register = await client.post(
        "/api/tools",
        json={
            "name": "dig",
            "displayName": "dig",
            "description": "DNS lookup tool",
            "category": "dns_domain_analysis",
            "capabilities": ["dns_lookup"],
            "supportedPlatforms": ["LINUX", "MACOS"],
            "sourceType": "official_website",
            "sourceUrl": "https://isc.org",
            "version": "9.18",
            "license": "MPL-2.0",
        },
    )
    tool_id = register.json()["id"]

    verify = await client.post(f"/api/tools/{tool_id}/verify")
    assert verify.status_code == 200
    assert verify.json()["trustStatus"] == "verified"

    approve = await client.post(f"/api/tools/{tool_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["trustStatus"] == "approved"

    eligibility = await client.get(
        f"/api/tools/{tool_id}/eligibility", params={"platform": "LINUX"}
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True
    _teardown()


async def test_approve_before_verify_is_rejected(client):
    _override()
    register = await client.post(
        "/api/tools",
        json={
            "name": "dig",
            "displayName": "dig",
            "description": "DNS lookup tool",
            "category": "dns_domain_analysis",
            "sourceType": "official_website",
        },
    )
    tool_id = register.json()["id"]

    approve = await client.post(f"/api/tools/{tool_id}/approve")
    assert approve.status_code == 409
    _teardown()


async def test_prohibited_capability_never_verifies_clean(client):
    _override()
    register = await client.post(
        "/api/tools",
        json={
            "name": "evil-tool",
            "displayName": "evil-tool",
            "description": "does bad things",
            "category": "developer_utilities",
            "capabilities": ["credential_theft"],
            "sourceType": "official_website",
        },
    )
    tool_id = register.json()["id"]

    verify = await client.post(f"/api/tools/{tool_id}/verify")
    assert verify.json()["trustStatus"] == "blocked"
    _teardown()


async def test_list_and_search_tools(client):
    _override()
    await client.post(
        "/api/tools",
        json={
            "name": "dig",
            "displayName": "dig",
            "description": "DNS lookup tool",
            "category": "dns_domain_analysis",
            "capabilities": ["dns_lookup"],
            "sourceType": "official_website",
        },
    )
    await client.post(
        "/api/tools",
        json={
            "name": "nmap",
            "displayName": "Nmap",
            "description": "Network scanner",
            "category": "network_diagnostics",
            "capabilities": ["port_scan"],
            "sourceType": "official_website",
        },
    )

    all_tools = await client.get("/api/tools")
    assert len(all_tools.json()) == 2

    filtered = await client.get("/api/tools", params={"category": "network_diagnostics"})
    assert [t["name"] for t in filtered.json()] == ["nmap"]

    searched = await client.get("/api/tools", params={"search": "dns_lookup"})
    assert [t["name"] for t in searched.json()] == ["dig"]
    _teardown()


async def test_no_execute_tool_endpoint_exists(client):
    """Regression guard: this phase must never introduce an unrestricted
    tool-execution endpoint."""
    response = await client.post("/api/execute-tool", json={})
    assert response.status_code == 404

    paths = {getattr(r, "path", "") for r in tools_routes.router.routes}
    assert not any("execute" in p for p in paths)
