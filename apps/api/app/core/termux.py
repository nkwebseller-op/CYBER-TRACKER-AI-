"""Process-wide Termux connector singletons, configured from Settings.

Singletons (not per-request instances) for the same reason as
get_terminal_engine(): device/pairing/connection state is held in-memory
for this phase — a later phase can back PairingService with the database
without changing its interface.
"""

from functools import lru_cache

from services.termux.config import TermuxConnectorConfig
from services.termux.connection_manager import TermuxConnectionManager
from services.termux.pairing import PairingService

from app.core.config import get_settings


@lru_cache
def get_termux_config() -> TermuxConnectorConfig:
    settings = get_settings()
    return TermuxConnectorConfig(
        pairing_code_ttl_seconds=settings.termux_pairing_code_ttl_seconds,
        max_registered_devices=settings.termux_max_registered_devices,
    )


@lru_cache
def get_pairing_service() -> PairingService:
    config = get_termux_config()
    return PairingService(pairing_code_ttl_seconds=config.pairing_code_ttl_seconds)


@lru_cache
def get_connection_manager() -> TermuxConnectionManager:
    config = get_termux_config()
    return TermuxConnectionManager(
        get_pairing_service(), cancel_grace_seconds=config.cancel_grace_seconds
    )
