"""WebSocket gateway for authenticated Termux device connections.

    Termux connector app
          |  wss:// (TLS terminated by the ASGI server/reverse proxy,
          |  same as every other route in this API — see
          |  services/termux/connection_manager.py's module docstring)
          v
    /ws/termux  (this file)
          |
    TermuxConnectionManager.handle_connect / handle_inbound_message

Protocol (JSON messages both ways):

  Device -> server, first message, required:
    {"type": "auth", "deviceId": "<uuid>", "deviceToken": "<token>"}

  Server -> device, after successful auth:
    {"type": "auth_ok"}
  or, and the socket is then closed:
    {"type": "auth_failed", "code": "<TermuxErrorCode>", "message": "..."}

  After auth, inbound device -> server messages are dispatched to
  TermuxConnectionManager.handle_inbound_message (stdout/stderr/
  command_completed/command_failed); outbound server -> device messages
  (command_request/command_cancel) are sent directly by
  TermuxConnectionManager.execute() via the transport this module hands it.

A device never gets more than one chance to authenticate per connection —
a failed `auth` message closes the socket immediately rather than allowing
retries over the same connection, which would otherwise make this an easy
credential-guessing oracle.
"""

from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from services.termux.connection_manager import TermuxConnectionManager
from services.termux.errors import MalformedMessageError, TermuxConnectorError

from app.core.logging import get_logger

logger = get_logger(__name__)


class _WebSocketTransport:
    """Adapts FastAPI's WebSocket to the minimal `TermuxTransport` protocol
    TermuxConnectionManager depends on, keeping services/termux free of any
    web-framework import."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def send_json(self, message: dict) -> None:
        await self._websocket.send_json(message)


async def termux_websocket_endpoint(
    websocket: WebSocket, manager: TermuxConnectionManager
) -> None:
    await websocket.accept()

    device_id: UUID | None = None
    try:
        auth_message = await websocket.receive_json()
    except Exception:  # noqa: BLE001 - malformed handshake, never a stack trace to the client
        await websocket.close(code=4400)
        return

    if not isinstance(auth_message, dict) or auth_message.get("type") != "auth":
        await websocket.send_json(
            {"type": "auth_failed", "code": "malformed_request", "message": "Expected auth first."}
        )
        await websocket.close(code=4400)
        return

    try:
        device_id = UUID(str(auth_message.get("deviceId")))
        device_token = str(auth_message.get("deviceToken", ""))
        transport = _WebSocketTransport(websocket)
        await manager.handle_connect(device_id, device_token, transport)
    except (TermuxConnectorError, ValueError) as exc:
        code = exc.code.value if isinstance(exc, TermuxConnectorError) else "malformed_request"
        await websocket.send_json({"type": "auth_failed", "code": code, "message": str(exc)})
        await websocket.close(code=4401)
        return

    await websocket.send_json({"type": "auth_ok"})

    try:
        while True:
            message = await websocket.receive_json()
            try:
                manager.handle_inbound_message(device_id, message)
            except MalformedMessageError as exc:
                logger.warning("termux_malformed_message", device_id=str(device_id), error=str(exc))
    except WebSocketDisconnect:
        pass
    finally:
        manager.handle_disconnect(device_id)
