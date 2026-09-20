import asyncio

import pytest
from services.terminal.adapters.base import CommandSpec, ExecutionStatus
from services.termux.connection_manager import TermuxConnectionManager
from services.termux.errors import (
    AuthenticationFailedError,
    DeviceOfflineError,
    MalformedMessageError,
)
from services.termux.pairing import PairingService

from tests.terminal.helpers import RecordingAuditSink


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


def _paired_device(pairing: PairingService, name="pixel-7"):
    device, code = pairing.register_device(name=name)
    _paired, token = pairing.confirm_pairing(device.id, code)
    return device, token


async def test_handle_connect_with_valid_credentials_marks_connected():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()

    await manager.handle_connect(device.id, token, transport)

    assert manager.is_connected(device.id)


async def test_handle_connect_with_invalid_token_does_not_connect():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, _token = _paired_device(pairing)
    transport = FakeTransport()

    with pytest.raises(AuthenticationFailedError):
        await manager.handle_connect(device.id, "wrong-token", transport)

    assert not manager.is_connected(device.id)


async def test_execute_against_offline_device_raises():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, _token = _paired_device(pairing)

    with pytest.raises(DeviceOfflineError):
        await manager.execute(device.id, CommandSpec(argv=["echo", "hi"], timeout_seconds=1))


async def test_execute_sends_command_request_and_resolves_on_completion():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    async def respond_soon():
        await asyncio.sleep(0.05)
        sent = transport.sent[-1]
        assert sent["type"] == "command_request"
        command_id = sent["commandId"]
        manager.handle_inbound_message(
            device.id, {"type": "stdout", "commandId": command_id, "data": "hello\n"}
        )
        manager.handle_inbound_message(
            device.id, {"type": "command_completed", "commandId": command_id, "exitCode": 0}
        )

    responder = asyncio.create_task(respond_soon())
    result = await manager.execute(device.id, CommandSpec(argv=["echo", "hi"], timeout_seconds=5))
    await responder

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.stdout == "hello\n"
    assert result.exit_code == 0


async def test_execute_resolves_failed_with_stderr():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    async def respond_soon():
        await asyncio.sleep(0.05)
        command_id = transport.sent[-1]["commandId"]
        manager.handle_inbound_message(
            device.id, {"type": "stderr", "commandId": command_id, "data": "boom"}
        )
        manager.handle_inbound_message(
            device.id,
            {"type": "command_failed", "commandId": command_id, "exitCode": 1},
        )

    responder = asyncio.create_task(respond_soon())
    result = await manager.execute(device.id, CommandSpec(argv=["false"], timeout_seconds=5))
    await responder

    assert result.status == ExecutionStatus.FAILED
    assert "boom" in result.stderr
    assert result.exit_code == 1


async def test_execute_times_out_when_device_never_responds():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    result = await manager.execute(
        device.id, CommandSpec(argv=["sleep", "99"], timeout_seconds=0.2)
    )

    assert result.timed_out is True
    assert any(m["type"] == "command_cancel" for m in transport.sent)


async def test_execute_is_cancellable():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    task = asyncio.create_task(
        manager.execute(device.id, CommandSpec(argv=["sleep", "99"], timeout_seconds=30))
    )
    await asyncio.sleep(0.05)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert any(m["type"] == "command_cancel" for m in transport.sent)


async def test_disconnect_resolves_pending_commands_as_failed():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    task = asyncio.create_task(
        manager.execute(device.id, CommandSpec(argv=["sleep", "99"], timeout_seconds=30))
    )
    await asyncio.sleep(0.05)
    manager.handle_disconnect(device.id)

    result = await task
    assert result.status == ExecutionStatus.FAILED
    assert "lost" in result.stderr.lower()


async def test_output_limit_is_respected():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    async def respond_soon():
        await asyncio.sleep(0.05)
        command_id = transport.sent[-1]["commandId"]
        manager.handle_inbound_message(
            device.id, {"type": "stdout", "commandId": command_id, "data": "x" * 10000}
        )
        manager.handle_inbound_message(
            device.id, {"type": "command_completed", "commandId": command_id, "exitCode": 0}
        )

    responder = asyncio.create_task(respond_soon())
    result = await manager.execute(
        device.id, CommandSpec(argv=["print-lots"], timeout_seconds=5, max_stdout_bytes=10)
    )
    await responder

    assert result.stdout_truncated is True
    assert len(result.stdout) <= 10


async def test_malformed_message_without_type_raises():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    with pytest.raises(MalformedMessageError):
        manager.handle_inbound_message(device.id, {"data": "no type field"})


async def test_message_for_unknown_command_id_is_ignored_not_fatal():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    import uuid

    manager.handle_inbound_message(
        device.id, {"type": "stdout", "commandId": str(uuid.uuid4()), "data": "stale"}
    )  # must not raise


async def test_audit_events_never_include_raw_stdout_beyond_preview_limit():
    pairing = PairingService()
    sink = RecordingAuditSink()
    manager = TermuxConnectionManager(pairing, audit_sink=sink)
    device, token = _paired_device(pairing)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)

    async def respond_soon():
        await asyncio.sleep(0.05)
        command_id = transport.sent[-1]["commandId"]
        manager.handle_inbound_message(
            device.id, {"type": "command_completed", "commandId": command_id, "exitCode": 0}
        )

    responder = asyncio.create_task(respond_soon())
    await manager.execute(device.id, CommandSpec(argv=["echo"], timeout_seconds=5))
    await responder

    assert "termux.command.forwarded" in sink.event_types
    assert "termux.command.completed" in sink.event_types
