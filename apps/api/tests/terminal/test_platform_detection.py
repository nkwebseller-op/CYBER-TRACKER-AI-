from services.terminal.platform_types import (
    PlatformIdentifier,
    detect_platform,
    is_wsl,
    platform_for_adapter_name,
)


def test_detect_platform_returns_known_identifier():
    assert detect_platform() in set(PlatformIdentifier)


def test_termux_is_never_classified_as_plain_linux(monkeypatch):
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    assert detect_platform() == PlatformIdentifier.ANDROID_TERMUX


def test_platform_for_adapter_name_round_trips():
    assert platform_for_adapter_name("linux") == PlatformIdentifier.LINUX
    assert platform_for_adapter_name("macos") == PlatformIdentifier.MACOS
    assert platform_for_adapter_name("windows") == PlatformIdentifier.WINDOWS
    assert platform_for_adapter_name("termux") == PlatformIdentifier.ANDROID_TERMUX


def test_unknown_adapter_name_maps_to_unknown():
    assert platform_for_adapter_name("some-future-os") == PlatformIdentifier.UNKNOWN


def test_is_wsl_detects_wsl_distro_env_var(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    assert is_wsl() is True


def test_is_wsl_false_on_plain_linux(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert is_wsl() is False


def test_is_wsl_false_on_windows(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    assert is_wsl() is False


def test_wsl_is_never_classified_as_windows(monkeypatch):
    """The scenario the phase explicitly calls out: WSL must never be
    silently treated as native Windows."""
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.delenv("PREFIX", raising=False)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    assert detect_platform() == PlatformIdentifier.LINUX
    assert is_wsl() is True
