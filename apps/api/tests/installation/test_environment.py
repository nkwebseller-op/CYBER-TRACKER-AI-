from services.installation.environment import EnvironmentInspector
from services.installation.models import PackageManager
from services.terminal.platform_types import PlatformIdentifier


def test_inspect_reports_real_host_platform():
    check = EnvironmentInspector().inspect()
    assert check.platform in {p.value for p in PlatformIdentifier}
    assert check.architecture


def test_inspect_never_assumes_a_package_manager_without_checking(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    check = EnvironmentInspector().inspect(identifier=PlatformIdentifier.LINUX)
    assert check.available_package_managers == ()
    assert check.notes


def _which_only(expected: str, path: str):
    return lambda name: path if name == expected else None


def test_inspect_detects_available_package_manager(monkeypatch):
    monkeypatch.setattr("shutil.which", _which_only("apt-get", "/usr/bin/apt-get"))
    check = EnvironmentInspector().inspect(identifier=PlatformIdentifier.LINUX)
    assert PackageManager.APT in check.available_package_managers


def test_inspect_uses_platform_specific_candidates_for_windows(monkeypatch):
    monkeypatch.setattr("shutil.which", _which_only("winget", "C:/winget.exe"))
    check = EnvironmentInspector().inspect(identifier=PlatformIdentifier.WINDOWS)
    assert PackageManager.WINGET in check.available_package_managers
    assert PackageManager.APT not in check.available_package_managers


def test_inspect_uses_platform_specific_candidates_for_macos(monkeypatch):
    monkeypatch.setattr("shutil.which", _which_only("brew", "/opt/homebrew/bin/brew"))
    check = EnvironmentInspector().inspect(identifier=PlatformIdentifier.MACOS)
    assert PackageManager.BREW in check.available_package_managers


def test_inspect_uses_platform_specific_candidates_for_termux(monkeypatch):
    termux_pkg = "/data/data/com.termux/files/usr/bin/pkg"
    monkeypatch.setattr("shutil.which", _which_only("pkg", termux_pkg))
    check = EnvironmentInspector().inspect(identifier=PlatformIdentifier.ANDROID_TERMUX)
    assert PackageManager.TERMUX_PKG in check.available_package_managers
