"""Vetted command templates keyed by action type.

This is the only place argv is ever produced for a real execution. The AI
never sends shell text that reaches a process — it can only request an
`action_type`, which is looked up here *after* the Policy Engine has
already ALLOWed it (see services/terminal/engine.py). If an action type
has no template here, execution is refused — there is no fallback to
"run whatever the caller sent."

Deliberately tiny in this phase: one harmless, cross-platform diagnostic
command so the full pipeline (policy -> engine -> adapter -> result) can
be exercised end-to-end without any real tool being registered yet.

Phase 11 (services/installation) adds two *parameterized* templates —
`build_install_command` / `build_verification_command` — for installing
and verifying an APPROVED Trusted Tool Registry entry via a fixed set of
known package managers. These stay in this module because the same
invariant applies: a package name/version is validated against a strict
allowlist pattern here, and only here, before it can ever become argv —
services/installation never builds a shell string itself. The *type* of
operation ("install via winget/apt/dnf/pacman/brew/pip/pkg, name+version
regex-validated") is what's reviewed and registered
(see ACTION_RISK_TIERS below), the same way "diagnostics.echo_test" is a
reviewed action type — never raw text from a user, the AI, or a tool's
own self-reported metadata.
"""

import re
import sys
from collections.abc import Callable

from services.policy.engine import RiskTier
from services.terminal.errors import InvalidRequestError

CommandTemplate = Callable[[], list[str]]

# Deliberately conservative: package/version/executable "names" a package
# manager or filesystem would accept, nothing that could be interpreted as
# a flag, path traversal, or shell metacharacter.
_PACKAGE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_EXECUTABLE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")

INSTALL_ACTION_TYPE = "tool_install.package_manager_install"
VERIFY_ACTION_TYPE = "tool_install.package_manager_verify"


def _validate(pattern: re.Pattern[str], value: str, label: str) -> str:
    if not pattern.match(value):
        raise InvalidRequestError(f"Invalid {label} for installation: {value!r}")
    return value


def build_install_command(
    package_manager: str, package_name: str, version: str | None = None
) -> list[str]:
    """The only place install argv is produced. `package_manager` must be
    one of the fixed, reviewed values below — anything else is refused,
    never passed through as a shell command."""
    name = _validate(_PACKAGE_NAME_PATTERN, package_name, "package name")
    ver = _validate(_VERSION_PATTERN, version, "version") if version else None

    if package_manager == "winget":
        argv = [
            "winget",
            "install",
            "--id",
            name,
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        if ver:
            argv += ["--version", ver]
        return argv
    if package_manager == "apt":
        return ["apt-get", "install", "-y", f"{name}={ver}" if ver else name]
    if package_manager == "dnf":
        return ["dnf", "install", "-y", f"{name}-{ver}" if ver else name]
    if package_manager == "pacman":
        return ["pacman", "-S", "--noconfirm", name]
    if package_manager == "brew":
        return ["brew", "install", f"{name}@{ver}" if ver else name]
    if package_manager == "pip":
        return [sys.executable, "-m", "pip", "install", f"{name}=={ver}" if ver else name]
    if package_manager == "termux_pkg":
        return ["pkg", "install", "-y", name]
    raise InvalidRequestError(f"Unsupported package manager '{package_manager}'.")


def build_verification_command(
    package_manager: str, package_name: str, *, entrypoint: str | None = None
) -> list[str]:
    """A harmless, read-only command that reports whether a package is
    installed — never the install command re-run, and never anything
    that could mutate system state."""
    if entrypoint:
        exe = _validate(_EXECUTABLE_NAME_PATTERN, entrypoint, "entrypoint")
        return [exe, "--version"]

    name = _validate(_PACKAGE_NAME_PATTERN, package_name, "package name")
    if package_manager == "pip":
        return [sys.executable, "-m", "pip", "show", name]
    if package_manager == "brew":
        return ["brew", "list", "--versions", name]
    if package_manager == "winget":
        return ["winget", "list", "--id", name]
    if package_manager == "apt":
        return ["dpkg-query", "-W", "-f=${Version}", name]
    if package_manager == "dnf":
        return ["rpm", "-q", name]
    if package_manager == "pacman":
        return ["pacman", "-Q", name]
    if package_manager == "termux_pkg":
        return ["pkg", "list-installed", name]
    raise InvalidRequestError(f"Unsupported package manager '{package_manager}'.")


def _diagnostics_echo_test() -> list[str]:
    # Uses the running interpreter itself rather than a shell builtin like
    # `echo`, which isn't a real executable on every platform (notably
    # Windows) — this keeps the template genuinely cross-platform without
    # any per-OS branching.
    return [sys.executable, "-c", "print('cyberai-terminal-engine-ok')"]


COMMAND_TEMPLATES: dict[str, CommandTemplate] = {
    "diagnostics.echo_test": _diagnostics_echo_test,
}

# The server decides an action type's risk tier — a client-supplied risk
# level is never trusted for policy evaluation (see
# apps/api/app/api/routes/terminal.py).
ACTION_RISK_TIERS: dict[str, RiskTier] = {
    "diagnostics.echo_test": RiskTier.LOW,
    # A package install can run arbitrary vendor-controlled setup logic —
    # medium risk, requires approval (see services/policy/engine.py).
    INSTALL_ACTION_TYPE: RiskTier.MEDIUM,
    # A version/presence check is read-only — low risk, no approval needed.
    VERIFY_ACTION_TYPE: RiskTier.LOW,
}


def resolve_command(action_type: str) -> list[str] | None:
    template = COMMAND_TEMPLATES.get(action_type)
    return template() if template else None
