from services.terminal.platform_types import (
    PlatformIdentifier,
    detect_platform,
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
