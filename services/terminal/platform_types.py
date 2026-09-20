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
