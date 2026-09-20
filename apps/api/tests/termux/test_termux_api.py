from services.termux.pairing import PairingService

from app.core.termux import get_pairing_service
from app.main import app


async def _override_pairing() -> PairingService:
    pairing = PairingService()
    app.dependency_overrides[get_pairing_service] = lambda: pairing
    return pairing


async def test_register_device_returns_pairing_code(client):
    await _override_pairing()
    response = await client.post("/api/termux/devices/register", json={"name": "pixel-7"})

    assert response.status_code == 201
    body = response.json()
    assert body["device"]["state"] == "PAIRING_REQUIRED"
    assert body["device"]["platform"] == "ANDROID_TERMUX"
    assert isinstance(body["pairingCode"], str) and body["pairingCode"]

    app.dependency_overrides.pop(get_pairing_service, None)


async def test_full_pairing_flow_via_api(client):
    await _override_pairing()
    register = await client.post("/api/termux/devices/register", json={"name": "pixel-7"})
    device_id = register.json()["device"]["id"]
    pairing_code = register.json()["pairingCode"]

    pair = await client.post(
        f"/api/termux/devices/{device_id}/pair", json={"pairingCode": pairing_code}
    )

    assert pair.status_code == 200
    body = pair.json()
    assert body["device"]["state"] == "AUTHORIZED"
    assert isinstance(body["deviceToken"], str) and body["deviceToken"]

    app.dependency_overrides.pop(get_pairing_service, None)


async def test_pair_with_wrong_code_returns_400(client):
    await _override_pairing()
    register = await client.post("/api/termux/devices/register", json={"name": "pixel-7"})
    device_id = register.json()["device"]["id"]

    pair = await client.post(
        f"/api/termux/devices/{device_id}/pair", json={"pairingCode": "wrong"}
    )

    assert pair.status_code == 400
    app.dependency_overrides.pop(get_pairing_service, None)


async def test_pair_unregistered_device_returns_404(client):
    await _override_pairing()
    from uuid import uuid4

    pair = await client.post(
        f"/api/termux/devices/{uuid4()}/pair", json={"pairingCode": "anything"}
    )

    assert pair.status_code == 404
    app.dependency_overrides.pop(get_pairing_service, None)


async def test_list_devices_never_includes_pairing_code_or_token(client):
    await _override_pairing()
    register = await client.post("/api/termux/devices/register", json={"name": "pixel-7"})
    device_id = register.json()["device"]["id"]
    pairing_code = register.json()["pairingCode"]
    pair = await client.post(
        f"/api/termux/devices/{device_id}/pair", json={"pairingCode": pairing_code}
    )
    device_token = pair.json()["deviceToken"]

    listing = await client.get("/api/termux/devices")

    assert listing.status_code == 200
    serialized = listing.text
    assert pairing_code not in serialized
    assert device_token not in serialized

    app.dependency_overrides.pop(get_pairing_service, None)


async def test_revoke_device_via_api(client):
    await _override_pairing()
    register = await client.post("/api/termux/devices/register", json={"name": "pixel-7"})
    device_id = register.json()["device"]["id"]

    revoke = await client.post(f"/api/termux/devices/{device_id}/revoke")

    assert revoke.status_code == 200
    assert revoke.json()["state"] == "REVOKED"
    app.dependency_overrides.pop(get_pairing_service, None)


async def test_get_unknown_device_returns_404(client):
    await _override_pairing()
    from uuid import uuid4

    response = await client.get(f"/api/termux/devices/{uuid4()}")

    assert response.status_code == 404
    app.dependency_overrides.pop(get_pairing_service, None)
