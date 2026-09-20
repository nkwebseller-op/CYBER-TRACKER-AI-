"""WebSocket gateway tests using a fake WebSocket (no real network socket) —
exercises the auth handshake and message-dispatch logic directly."""

from services.termux.connection_manager import TermuxConnectionManager
from services.termux.pairing import PairingService

from app.ws.termux_gateway import termux_websocket_endpoint


class FakeWebSocket:
    def __init__(self, inbound: list[dict]) -> None:
        self._inbound = list(inbound)
        self.sent: list[dict] = []
        self.accepted = False
        self.closed_with: int | None = None

    async def accept(self) -> None:
        self.accepted = True

    async def receive_json(self) -> dict:
        if not self._inbound:
            from fastapi import WebSocketDisconnect

            raise WebSocketDisconnect()
        return self._inbound.pop(0)

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)

    async def close(self, code: int = 1000) -> None:
        self.closed_with = code


def _paired_device(pairing: PairingService):
    device, code = pairing.register_device(name="pixel-7")
    _paired, token = pairing.confirm_pairing(device.id, code)
    return device, token


async def test_successful_auth_handshake_sends_auth_ok():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)

    ws = FakeWebSocket(
        [{"type": "auth", "deviceId": str(device.id), "deviceToken": token}]
    )
    await termux_websocket_endpoint(ws, manager)

    assert ws.accepted is True
    assert {"type": "auth_ok"} in ws.sent
    assert not manager.is_connected(device.id)  # disconnected once receive_json raised


async def test_failed_auth_closes_connection_without_connecting():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, _token = _paired_device(pairing)

    ws = FakeWebSocket(
        [{"type": "auth", "deviceId": str(device.id), "deviceToken": "wrong-token"}]
    )
    await termux_websocket_endpoint(ws, manager)

    assert ws.closed_with == 4401
    assert any(m["type"] == "auth_failed" for m in ws.sent)
    assert not manager.is_connected(device.id)


async def test_non_auth_first_message_is_rejected():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)

    ws = FakeWebSocket([{"type": "stdout", "commandId": "x", "data": "hi"}])
    await termux_websocket_endpoint(ws, manager)

    assert ws.closed_with == 4400
    assert any(m["type"] == "auth_failed" for m in ws.sent)


async def test_inbound_messages_after_auth_are_dispatched_to_manager():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)

    ws = FakeWebSocket(
        [
            {"type": "auth", "deviceId": str(device.id), "deviceToken": token},
            {"type": "stdout", "commandId": "00000000-0000-0000-0000-000000000000", "data": "hi"},
        ]
    )
    await termux_websocket_endpoint(ws, manager)  # must not raise even for an unknown commandId

    assert {"type": "auth_ok"} in ws.sent
