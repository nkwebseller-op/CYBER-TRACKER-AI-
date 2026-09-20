"""Terminal Engine configuration. A plain dataclass with safe defaults —
services/ stays decoupled from apps/api's settings system; the API layer
constructs one of these from its own Settings when it builds the engine.
"""

import tempfile
from dataclasses import dataclass, field

from services.terminal.validation import DEFAULT_ENV_ALLOWLIST


@dataclass(frozen=True)
class TerminalEngineConfig:
    workspace_root: str = field(default_factory=tempfile.gettempdir)

    default_timeout_seconds: int = 30
    max_timeout_seconds: int = 120

    max_stdout_bytes: int = 1_000_000  # 1 MB
    max_stderr_bytes: int = 1_000_000

    session_ttl_seconds: int = 900  # 15 minutes of inactivity
    max_concurrent_sessions: int = 20

    env_allowlist: tuple[str, ...] = DEFAULT_ENV_ALLOWLIST

    # Windows-specific: PowerShell executable path override. None means
    # "auto-detect" (see services.terminal.adapters.windows.resolve_powershell_executable) —
    # every other Windows-adapter setting (timeouts, output caps, workspace
    # root, session limits) reuses the fields above rather than duplicating
    # them, per the "centralized configuration" requirement.
    windows_powershell_path: str | None = None

    def clamp_timeout(self, requested_seconds: int | None) -> int:
        if requested_seconds is None:
            return self.default_timeout_seconds
        return max(1, min(requested_seconds, self.max_timeout_seconds))
