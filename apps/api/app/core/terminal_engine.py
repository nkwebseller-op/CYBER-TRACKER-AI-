"""Process-wide TerminalEngine singleton, configured from Settings.

A singleton (not a per-request instance) because sessions are held
in-memory for this phase — see services/terminal/session_manager.py.
"""

from functools import lru_cache

from services.terminal.config import TerminalEngineConfig
from services.terminal.engine import TerminalEngine

from app.core.config import get_settings


@lru_cache
def get_terminal_engine() -> TerminalEngine:
    settings = get_settings()
    defaults = TerminalEngineConfig()

    config = TerminalEngineConfig(
        workspace_root=settings.terminal_workspace_root or defaults.workspace_root,
        default_timeout_seconds=settings.terminal_default_timeout_seconds,
        max_timeout_seconds=settings.terminal_max_timeout_seconds,
        max_stdout_bytes=settings.terminal_max_stdout_bytes,
        max_stderr_bytes=settings.terminal_max_stderr_bytes,
        session_ttl_seconds=settings.terminal_session_ttl_seconds,
        max_concurrent_sessions=settings.terminal_max_concurrent_sessions,
        windows_powershell_path=settings.terminal_windows_powershell_path,
        linux_shell_path=settings.terminal_linux_shell_path,
        macos_shell_path=settings.terminal_macos_shell_path,
    )
    return TerminalEngine(config=config)
