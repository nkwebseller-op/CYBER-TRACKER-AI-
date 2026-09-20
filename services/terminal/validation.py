"""Request-time validation shared by the Terminal Engine: working
directory confinement and environment variable filtering. Both run before
any process is created — a rejection here never touches the OS.
"""

import os
import re

from services.terminal.errors import InvalidRequestError, InvalidWorkingDirectoryError

# Host environment variables considered safe to let a controlled command
# see. Deliberately small and explicit — anything not listed here is never
# inherited unless the caller adds it, and nothing matching
# SECRET_KEY_PATTERN is ever added even then (see filter_environment).
DEFAULT_ENV_ALLOWLIST: tuple[str, ...] = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TZ",
    "TMPDIR",
    "TEMP",
    "TMP",
)

# Matches env var *names* that commonly carry secrets, regardless of what
# the caller asked to pass through — belt-and-suspenders on top of the
# allowlist above.
_SECRET_KEY_PATTERN = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY|PRIVATE[_-]?KEY|CREDENTIAL|_KEY$)", re.IGNORECASE
)

_MAX_COMMAND_ARGS = 64
_MAX_ARG_LENGTH = 4096


def filter_environment(overrides: dict[str, str]) -> dict[str, str]:
    """Strips anything that looks like a secret from caller-supplied
    environment overrides. This does not decide what's inherited from the
    host process — that's `CommandSpec.env_allowlist` — it only guards the
    explicit overrides a caller tried to add."""
    return {key: value for key, value in overrides.items() if not _SECRET_KEY_PATTERN.search(key)}


def validate_working_directory(path: str | None, *, workspace_root: str) -> str:
    """Resolves `path` relative to `workspace_root` and rejects anything
    that would escape it (`..`, absolute paths outside the root, symlink
    tricks resolved via realpath). Returns the resolved, safe path."""
    root = os.path.realpath(workspace_root)

    if path is None or path in ("", "."):
        return root

    candidate = path if os.path.isabs(path) else os.path.join(root, path)
    resolved = os.path.realpath(candidate)

    if resolved != root and not resolved.startswith(root + os.sep):
        raise InvalidWorkingDirectoryError(
            "The requested working directory is outside the allowed workspace."
        )

    return resolved


def validate_argv(argv: list[str]) -> None:
    if not isinstance(argv, list) or len(argv) == 0:
        raise InvalidRequestError("Command must be a non-empty list of arguments.")
    if not all(isinstance(arg, str) for arg in argv):
        raise InvalidRequestError("Every command argument must be a string.")
    if len(argv) > _MAX_COMMAND_ARGS:
        raise InvalidRequestError(f"Command has too many arguments (limit is {_MAX_COMMAND_ARGS}).")
    if any(len(arg) > _MAX_ARG_LENGTH for arg in argv):
        raise InvalidRequestError(
            f"A command argument exceeds the maximum length ({_MAX_ARG_LENGTH})."
        )
