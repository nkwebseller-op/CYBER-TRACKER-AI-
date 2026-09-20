"""Environment detection — read-only introspection of the server's own
runtime, never a mutation, so it never needs to go through the Policy
Engine (the same reasoning Phase 6-8 adapters' `get_capabilities()`
already rely on for shell resolution).

Reuses the platform-specific shell resolvers already built in Phase 6-8
instead of re-detecting shells here — "integrate, don't duplicate."
"""

import platform
import shutil
import sys

from services.installation.models import EnvironmentCheck, PackageManager
from services.terminal.platform_types import PlatformIdentifier, detect_platform

_PACKAGE_MANAGER_EXECUTABLE = {
    PackageManager.WINGET: "winget",
    PackageManager.APT: "apt-get",
    PackageManager.DNF: "dnf",
    PackageManager.PACMAN: "pacman",
    PackageManager.BREW: "brew",
    PackageManager.TERMUX_PKG: "pkg",
}

# Candidate package managers per platform — never assumes one works
# everywhere (a Fedora host has no apt, a Debian host has no dnf, etc.).
_CANDIDATES_BY_PLATFORM: dict[PlatformIdentifier, tuple[PackageManager, ...]] = {
    PlatformIdentifier.WINDOWS: (PackageManager.WINGET, PackageManager.PIP),
    PlatformIdentifier.LINUX: (
        PackageManager.APT,
        PackageManager.DNF,
        PackageManager.PACMAN,
        PackageManager.PIP,
    ),
    PlatformIdentifier.MACOS: (PackageManager.BREW, PackageManager.PIP),
    PlatformIdentifier.ANDROID_TERMUX: (PackageManager.TERMUX_PKG, PackageManager.PIP),
}


def _resolve_shell(identifier: PlatformIdentifier) -> str | None:
    """Delegates to the same adapter classes Phase 6-8 already built for
    shell resolution, rather than re-implementing shell discovery here."""
    if identifier == PlatformIdentifier.WINDOWS:
        from services.terminal.adapters.windows import resolve_powershell_executable

        return resolve_powershell_executable()
    if identifier == PlatformIdentifier.LINUX:
        from services.terminal.adapters.linux import resolve_linux_shell

        return resolve_linux_shell()
    if identifier == PlatformIdentifier.MACOS:
        from services.terminal.adapters.macos import resolve_macos_shell

        return resolve_macos_shell()
    return None


class EnvironmentInspector:
    def inspect(self, *, identifier: PlatformIdentifier | None = None) -> EnvironmentCheck:
        platform_id = identifier or detect_platform()
        candidates = _CANDIDATES_BY_PLATFORM.get(platform_id, (PackageManager.PIP,))

        available: list[PackageManager] = []
        for manager in candidates:
            if manager == PackageManager.PIP:
                if shutil.which("pip") or shutil.which("pip3"):
                    available.append(manager)
                continue
            executable = _PACKAGE_MANAGER_EXECUTABLE.get(manager)
            if executable and shutil.which(executable):
                available.append(manager)

        notes: list[str] = []
        if not available:
            notes.append(
                f"No known package manager was found on PATH for platform {platform_id.value}."
            )

        return EnvironmentCheck(
            platform=platform_id.value,
            architecture=platform.machine() or "unknown",
            shell=_resolve_shell(platform_id),
            available_package_managers=tuple(available),
            python_version=sys.version.split()[0],
            notes=tuple(notes),
        )
