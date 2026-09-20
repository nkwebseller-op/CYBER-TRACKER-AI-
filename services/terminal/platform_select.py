"""Detects the current OS/runtime and returns the matching adapter."""

import os
import platform

from services.terminal.adapters.base import TerminalAdapter


def is_termux() -> bool:
    return "com.termux" in os.environ.get("PREFIX", "")


def select_adapter() -> TerminalAdapter:
    if is_termux():
        from services.terminal.adapters.termux import TermuxAdapter

        return TermuxAdapter()

    system = platform.system()
    if system == "Linux":
        from services.terminal.adapters.linux import LinuxAdapter

        return LinuxAdapter()
    if system == "Darwin":
        from services.terminal.adapters.macos import MacOSAdapter

        return MacOSAdapter()
    if system == "Windows":
        from services.terminal.adapters.windows import WindowsAdapter

        return WindowsAdapter()

    raise RuntimeError(f"Unsupported platform: {system!r}")
