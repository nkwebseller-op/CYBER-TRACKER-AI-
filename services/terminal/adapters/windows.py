from services.terminal.adapters.local_process import LocalProcessAdapter


class WindowsAdapter(LocalProcessAdapter):
    """Windows adapter. Uses the same argv-based subprocess execution as the
    POSIX adapters (no shell=True), so PATH resolution and .exe/.cmd
    extension handling relies on Python's own subprocess machinery rather
    than a shell."""

    name = "windows"
