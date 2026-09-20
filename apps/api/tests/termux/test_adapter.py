import asyncio

from services.policy.engine import PolicyDecision, PolicyVerdict
from services.terminal.adapters.base import ExecutionStatus
from services.terminal.config import TerminalEngineConfig
from services.terminal.engine import TerminalEngine
from services.terminal.models import CommandStatus, TerminalCommandRequest
from services.terminal.platform_types import PlatformIdentifier
from services.termux.adapter import RemoteTermuxAdapter
from services.termux.connection_manager import TermuxConnectionManager
from services.termux.pairing import PairingService

from tests.terminal.helpers import RecordingAuditSink, python_command

ALLOW = PolicyDecision(verdict=PolicyVerdict.ALLOW, reasons=["ok"])
DENY = PolicyDecision(verdict=PolicyVerdict.DENY, reasons=["nope"])


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


async def _connected_device():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, code = pairing.register_device(name="pixel-7")
    _paired, token = pairing.confirm_pairing(device.id, code)
    transport = FakeTransport()
    await manager.handle_connect(device.id, token, transport)
    return manager, device, transport


async def test_adapter_run_returns_failed_when_device_offline():
    pairing = PairingService()
    manager = TermuxConnectionManager(pairing)
    device, _code = pairing.register_device(name="pixel-7")

    adapter = RemoteTermuxAdapter(manager, device.id)
    from services.terminal.adapters.base import CommandSpec

    result = await adapter.run(CommandSpec(argv=["echo", "hi"], timeout_seconds=1))

    assert result.status == ExecutionStatus.FAILED
    assert "Traceback" not in (result.stderr or "")


async def test_engine_denies_execution_before_ever_contacting_device():
    """The adapter/connector must never see a DENY-ed command — the engine
    rejects it before `adapter.run()` is called at all."""
    manager, device, transport = await _connected_device()
    adapter = RemoteTermuxAdapter(manager, device.id)
    sink = RecordingAuditSink()
    engine = TerminalEngine(config=TerminalEngineConfig(), adapter=adapter, audit_sink=sink)
    session = engine.create_session()

    request = TerminalCommandRequest(
        session_id=session.id,
        command=python_command("print('should-not-run')"),
        authorization_context=DENY,
    )
    result = await engine.execute(request)

    assert result.status == CommandStatus.REJECTED
    assert transport.sent == []  # nothing was ever forwarded to the device


async def test_engine_forwards_allowed_command_through_adapter_to_device():
    manager, device, transport = await _connected_device()
    adapter = RemoteTermuxAdapter(manager, device.id)
    engine = TerminalEngine(config=TerminalEngineConfig(), adapter=adapter)
    session = engine.create_session()

    request = TerminalCommandRequest(
        session_id=session.id,
        command=["echo", "hello"],
        authorization_context=ALLOW,
    )

    async def respond_soon():
        await asyncio.sleep(0.05)
        command_id = transport.sent[-1]["commandId"]
        manager.handle_inbound_message(
            device.id, {"type": "stdout", "commandId": command_id, "data": "hello\n"}
        )
        manager.handle_inbound_message(
            device.id, {"type": "command_completed", "commandId": command_id, "exitCode": 0}
        )

    responder = asyncio.create_task(respond_soon())
    result = await engine.execute(request)
    await responder

    assert result.status == CommandStatus.COMPLETED
    assert result.stdout == "hello\n"
    assert result.platform == PlatformIdentifier.ANDROID_TERMUX


async def test_engine_reports_timeout_when_device_never_responds():
    manager, device, _transport = await _connected_device()
    adapter = RemoteTermuxAdapter(manager, device.id)
    engine = TerminalEngine(config=TerminalEngineConfig(default_timeout_seconds=1), adapter=adapter)
    session = engine.create_session()

    request = TerminalCommandRequest(
        session_id=session.id,
        command=["sleep", "99"],
        authorization_context=ALLOW,
    )
    result = await engine.execute(request)

    assert result.status == CommandStatus.TIMEOUT
