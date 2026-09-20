import pytest
from services.termux.errors import (
    AuthenticationFailedError,
    DeviceNotRegisteredError,
    PairingCodeExpiredError,
    PairingCodeInvalidError,
    RevokedDeviceError,
)
from services.termux.models import DeviceState, TermuxCapability
from services.termux.pairing import PairingService

from tests.terminal.helpers import RecordingAuditSink


def _service(**overrides) -> PairingService:
    sink = RecordingAuditSink()
    return PairingService(audit_sink=sink, **overrides)


def test_register_device_starts_in_pairing_required_state():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")

    assert device.state == DeviceState.PAIRING_REQUIRED
    assert isinstance(code, str) and len(code) > 0


def test_confirm_pairing_with_correct_code_authorizes_device():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")

    paired_device, token = pairing.confirm_pairing(device.id, code)

    assert paired_device.state == DeviceState.AUTHORIZED
    assert isinstance(token, str) and len(token) > 0


def test_confirm_pairing_with_wrong_code_is_rejected():
    pairing = _service()
    device, _code = pairing.register_device(name="pixel-7")

    with pytest.raises(PairingCodeInvalidError):
        pairing.confirm_pairing(device.id, "totally-wrong-code")


def test_confirm_pairing_code_is_single_use():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")
    pairing.confirm_pairing(device.id, code)

    with pytest.raises(PairingCodeInvalidError):
        pairing.confirm_pairing(device.id, code)


def test_expired_pairing_code_is_rejected(monkeypatch):
    pairing = _service(pairing_code_ttl_seconds=0)
    device, code = pairing.register_device(name="pixel-7")

    with pytest.raises(PairingCodeExpiredError):
        pairing.confirm_pairing(device.id, code)


def test_authenticate_with_correct_token_succeeds():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")
    _paired, token = pairing.confirm_pairing(device.id, code)

    authenticated = pairing.authenticate(device.id, token)
    assert authenticated.id == device.id


def test_authenticate_with_wrong_token_fails():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")
    pairing.confirm_pairing(device.id, code)

    with pytest.raises(AuthenticationFailedError):
        pairing.authenticate(device.id, "wrong-token")


def test_authenticate_unregistered_device_fails():
    pairing = _service()
    import uuid

    with pytest.raises(DeviceNotRegisteredError):
        pairing.authenticate(uuid.uuid4(), "any-token")


def test_revoked_device_cannot_authenticate():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")
    _paired, token = pairing.confirm_pairing(device.id, code)
    pairing.revoke_device(device.id)

    with pytest.raises(RevokedDeviceError):
        pairing.authenticate(device.id, token)


def test_revoke_sets_state_and_clears_credential():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")
    pairing.confirm_pairing(device.id, code)

    revoked = pairing.revoke_device(device.id)
    assert revoked.state == DeviceState.REVOKED
    assert revoked.revoked_at is not None


def test_connect_disconnect_transitions_state():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")
    pairing.confirm_pairing(device.id, code)

    connected = pairing.mark_connected(device.id)
    assert connected.state == DeviceState.CONNECTED

    disconnected = pairing.mark_disconnected(device.id)
    assert disconnected.state == DeviceState.DISCONNECTED


def test_device_capabilities_are_declared_not_assumed():
    pairing = _service()
    device, _code = pairing.register_device(
        name="pixel-7", capabilities=frozenset({TermuxCapability.TERMINAL_EXECUTION})
    )
    assert device.capabilities == frozenset({TermuxCapability.TERMINAL_EXECUTION})
    assert TermuxCapability.FILESYSTEM_ACCESS not in device.capabilities


def test_public_dict_never_includes_pairing_code_or_token():
    pairing = _service()
    device, code = pairing.register_device(name="pixel-7")
    _paired, token = pairing.confirm_pairing(device.id, code)

    public = device.to_public_dict()
    serialized = str(public)
    assert code not in serialized
    assert token not in serialized


def test_audit_events_never_include_raw_pairing_code_or_token():
    sink = RecordingAuditSink()
    pairing = PairingService(audit_sink=sink)
    device, code = pairing.register_device(name="pixel-7")
    _paired, token = pairing.confirm_pairing(device.id, code)
    pairing.revoke_device(device.id)

    for event in sink.events:
        serialized = str(event.data)
        assert code not in serialized
        assert token not in serialized
