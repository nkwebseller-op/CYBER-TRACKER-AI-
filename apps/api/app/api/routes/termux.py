"""Termux Connector API.

    Android device (Termux connector app)
          |
    POST /api/termux/devices/register   -> pairing code (out of band)
          |
    POST /api/termux/devices/{id}/pair  -> device token (returned once)
          |
    WebSocket /ws/termux                -> authenticated device connection
          |
    (an authorized operator action, via /api/terminal/execute-style
     policy gate elsewhere) -> RemoteTermuxAdapter -> TerminalEngine

This router only ever handles registration/pairing/status/revocation — it
has no endpoint that accepts a raw command for a device. Command execution
against a paired device goes through the same Policy Engine gate as every
other terminal execution (see apps/api/app/api/routes/terminal.py); wiring
a device-scoped `/execute` there is a direct extension of that existing
endpoint, tracked as a next-phase integration point rather than duplicated
here (see the Phase 9 summary).
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from services.termux.errors import TermuxConnectorError
from services.termux.pairing import PairingService

from app.core.errors import CyberAIError
from app.core.termux import get_pairing_service
from app.schemas.termux import (
    ConfirmPairingRequest,
    ConfirmPairingResponse,
    DeviceResponse,
    RegisterDeviceRequest,
    RegisterDeviceResponse,
)

router = APIRouter(prefix="/termux", tags=["termux"])

_ERROR_STATUS_BY_CODE = {
    "device_not_registered": 404,
    "pairing_code_invalid": 400,
    "pairing_code_expired": 400,
    "authentication_failed": 401,
    "revoked_device": 403,
}


class TermuxConnectorHTTPError(CyberAIError):
    def __init__(self, exc: TermuxConnectorError) -> None:
        super().__init__(str(exc))
        self.code = exc.code.value
        self.status_code = _ERROR_STATUS_BY_CODE.get(exc.code.value, 400)


@router.post("/devices/register", response_model=RegisterDeviceResponse, status_code=201)
async def register_device(
    request: RegisterDeviceRequest, pairing: PairingService = Depends(get_pairing_service)
) -> RegisterDeviceResponse:
    device, pairing_code = pairing.register_device(
        name=request.name,
        connector_version=request.connector_version,
        capabilities=frozenset(request.capabilities),
    )
    return RegisterDeviceResponse(
        device=DeviceResponse.model_validate(device.to_public_dict()),
        pairing_code=pairing_code,
        expires_in_seconds=pairing.pairing_code_ttl_seconds,
    )


@router.post("/devices/{device_id}/pair", response_model=ConfirmPairingResponse)
async def confirm_pairing(
    device_id: UUID,
    request: ConfirmPairingRequest,
    pairing: PairingService = Depends(get_pairing_service),
) -> ConfirmPairingResponse:
    try:
        device, device_token = pairing.confirm_pairing(device_id, request.pairing_code)
    except TermuxConnectorError as exc:
        raise TermuxConnectorHTTPError(exc) from exc
    return ConfirmPairingResponse(
        device=DeviceResponse.model_validate(device.to_public_dict()),
        device_token=device_token,
    )


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    pairing: PairingService = Depends(get_pairing_service),
) -> list[DeviceResponse]:
    return [DeviceResponse.model_validate(d.to_public_dict()) for d in pairing.list_devices()]


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID, pairing: PairingService = Depends(get_pairing_service)
) -> DeviceResponse:
    try:
        device = pairing.get_device(device_id)
    except TermuxConnectorError as exc:
        raise TermuxConnectorHTTPError(exc) from exc
    return DeviceResponse.model_validate(device.to_public_dict())


@router.post("/devices/{device_id}/revoke", response_model=DeviceResponse)
async def revoke_device(
    device_id: UUID, pairing: PairingService = Depends(get_pairing_service)
) -> DeviceResponse:
    try:
        device = pairing.revoke_device(device_id)
    except TermuxConnectorError as exc:
        raise TermuxConnectorHTTPError(exc) from exc
    return DeviceResponse.model_validate(device.to_public_dict())
