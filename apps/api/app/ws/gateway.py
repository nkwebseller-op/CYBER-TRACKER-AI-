"""WebSocket gateway for real-time streams: live terminal output and the AI
activity timeline. Phase 1 ships the connection lifecycle and a simple
broadcast hub; real event sources (execution controller, orchestrator
streaming) plug into `ConnectionHub.broadcast` in a later phase."""

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


hub = ConnectionHub()


async def websocket_endpoint(websocket: WebSocket) -> None:
    await hub.connect(websocket)
    try:
        while True:
            # Phase 1: echo/keepalive only. Real inbound events (approvals,
            # cancellations) are handled once the execution controller is wired
            # to the API in the next phase.
            data = await websocket.receive_json()
            await websocket.send_json({"type": "ack", "received": data})
    except WebSocketDisconnect:
        hub.disconnect(websocket)
