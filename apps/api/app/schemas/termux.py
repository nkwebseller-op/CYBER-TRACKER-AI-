"""Pydantic contracts for the Termux connector API. Deliberately narrow —
no endpoint here returns a stored pairing code or device token; the raw
one-time secret is returned exactly once, by the endpoint that mints it,
and never again by any GET."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from services.termux.models import DeviceState, TermuxCapability


class RegisterDeviceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_version: str | None = Field(default=None, alias="connectorVersion")
    capabilities: list[TermuxCapability] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class DeviceResponse(BaseModel):
    id: UUID
    name: str
    platform: str
    connector_version: str | None = Field(default=None, alias="connectorVersion")
    capabilities: list[str]
    state: DeviceState
    registered_at: datetime = Field(alias="registeredAt")
    last_seen_at: datetime | None = Field(default=None, alias="lastSeenAt")
    revoked_at: datetime | None = Field(default=None, alias="revokedAt")

    model_config = ConfigDict(populate_by_name=True)


class RegisterDeviceResponse(BaseModel):
    device: DeviceResponse
    pairing_code: str = Field(alias="pairingCode")
    expires_in_seconds: int = Field(alias="expiresInSeconds")

    model_config = ConfigDict(populate_by_name=True)


class ConfirmPairingRequest(BaseModel):
    pairing_code: str = Field(alias="pairingCode", min_length=1, max_length=64)

    model_config = ConfigDict(populate_by_name=True)


class ConfirmPairingResponse(BaseModel):
    device: DeviceResponse
    device_token: str = Field(alias="deviceToken")

    model_config = ConfigDict(populate_by_name=True)
