"""Selects the platform adapter matching the current runtime."""

from services.terminal.adapters.base import TerminalAdapter
from services.terminal.errors import UnsupportedPlatformError
from services.terminal.platform_types import PlatformIdentifier, detect_platform, is_termux

__all__ = ["is_termux", "select_adapter"]


def select_adapter() -> TerminalAdapter:
    identifier = detect_platform()

    if identifier == PlatformIdentifier.ANDROID_TERMUX:
        from services.terminal.adapters.termux import TermuxAdapter

        return TermuxAdapter()
    if identifier == PlatformIdentifier.LINUX:
        from services.terminal.adapters.linux import LinuxAdapter

        return LinuxAdapter()
    if identifier == PlatformIdentifier.MACOS:
        from services.terminal.adapters.macos import MacOSAdapter

        return MacOSAdapter()
    if identifier == PlatformIdentifier.WINDOWS:
        from services.terminal.adapters.windows import WindowsAdapter

        return WindowsAdapter()

    raise UnsupportedPlatformError(f"Unsupported platform: {identifier!r}")
