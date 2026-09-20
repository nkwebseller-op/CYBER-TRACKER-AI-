from services.terminal.adapters.linux import LinuxTerminalAdapter
from services.terminal.adapters.macos import MacOSTerminalAdapter
from services.terminal.adapters.windows import WindowsTerminalAdapter
from services.terminal.platform_select import select_adapter
from services.terminal.platform_types import PlatformIdentifier


def test_select_adapter_passes_powershell_path_on_windows(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.WINDOWS
    )

    adapter = select_adapter(windows_powershell_path="/custom/pwsh")

    assert isinstance(adapter, WindowsTerminalAdapter)
    assert adapter._configured_powershell_path == "/custom/pwsh"  # noqa: SLF001


def test_select_adapter_windows_defaults_to_auto_detect(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.WINDOWS
    )

    adapter = select_adapter()

    assert isinstance(adapter, WindowsTerminalAdapter)
    assert adapter._configured_powershell_path is None  # noqa: SLF001


def test_select_adapter_passes_shell_path_on_linux(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.LINUX
    )

    adapter = select_adapter(linux_shell_path="/custom/bash")

    assert isinstance(adapter, LinuxTerminalAdapter)
    assert adapter._configured_shell_path == "/custom/bash"  # noqa: SLF001


def test_select_adapter_linux_defaults_to_auto_detect(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.LINUX
    )

    adapter = select_adapter()

    assert isinstance(adapter, LinuxTerminalAdapter)
    assert adapter._configured_shell_path is None  # noqa: SLF001


def test_select_adapter_windows_not_routed_to_linux_adapter(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.WINDOWS
    )

    adapter = select_adapter()

    assert not isinstance(adapter, LinuxTerminalAdapter)


def test_select_adapter_passes_shell_path_on_macos(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.MACOS
    )

    adapter = select_adapter(macos_shell_path="/custom/zsh")

    assert isinstance(adapter, MacOSTerminalAdapter)
    assert adapter._configured_shell_path == "/custom/zsh"  # noqa: SLF001


def test_select_adapter_macos_defaults_to_auto_detect(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.MACOS
    )

    adapter = select_adapter()

    assert isinstance(adapter, MacOSTerminalAdapter)
    assert adapter._configured_shell_path is None  # noqa: SLF001


def test_select_adapter_macos_not_routed_to_linux_or_windows(monkeypatch):
    monkeypatch.setattr(
        "services.terminal.platform_select.detect_platform", lambda: PlatformIdentifier.MACOS
    )

    adapter = select_adapter()

    assert not isinstance(adapter, LinuxTerminalAdapter)
    assert not isinstance(adapter, WindowsTerminalAdapter)
