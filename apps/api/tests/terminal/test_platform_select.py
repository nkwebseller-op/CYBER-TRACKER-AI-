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
