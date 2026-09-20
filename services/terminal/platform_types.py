"""Platform identification for the Terminal Engine.

Android/Termux is never classified as ordinary Linux — the whole point of
a distinct ANDROID_TERMUX identifier is that later phases can give it its
own adapter, tool availability, and install strategy instead of silently
falling back to generic Linux behavior.
"""

import os
import platform
from enum import StrEnum


class PlatformIdentifier(StrEnum):
    WINDOWS = "WINDOWS"
    LINUX = "LINUX"
    MACOS = "MACOS"
    ANDROID_TERMUX = "ANDROID_TERMUX"
    UNKNOWN = "UNKNOWN"


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "")


def is_wsl() -> bool:
    """True when running inside Windows Subsystem for Linux.

    WSL reports `platform.system() == "Linux"` — it is correctly detected
    as LINUX by `detect_platform()`, never WINDOWS. This helper exists so
    callers that need to know they're specifically under WSL (rather than
    a bare-metal/VM Linux host) can check explicitly instead of that
    distinction silently disappearing into "just Linux".
    """
    if platform.system() != "Linux":
        return False
    if "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ:
        return True
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def detect_platform() -> PlatformIdentifier:
    if is_termux():
        return PlatformIdentifier.ANDROID_TERMUX

    system = platform.system()
    if system == "Linux":
        return PlatformIdentifier.LINUX
    if system == "Darwin":
        return PlatformIdentifier.MACOS
    if system == "Windows":
        return PlatformIdentifier.WINDOWS
    return PlatformIdentifier.UNKNOWN


# Adapter `.name` values (services/terminal/adapters/*.py) map 1:1 to these
# identifiers, lowercased — kept as an explicit table rather than a
# `.lower()` call at every call site so the mapping is visible in one place.
ADAPTER_NAME_BY_PLATFORM: dict[PlatformIdentifier, str] = {
    PlatformIdentifier.WINDOWS: "windows",
    PlatformIdentifier.LINUX: "linux",
    PlatformIdentifier.MACOS: "macos",
    PlatformIdentifier.ANDROID_TERMUX: "termux",
}

PLATFORM_BY_ADAPTER_NAME: dict[str, PlatformIdentifier] = {
    name: identifier for identifier, name in ADAPTER_NAME_BY_PLATFORM.items()
}


def platform_for_adapter_name(adapter_name: str) -> PlatformIdentifier:
    return PLATFORM_BY_ADAPTER_NAME.get(adapter_name, PlatformIdentifier.UNKNOWN)
