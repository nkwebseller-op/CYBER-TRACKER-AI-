from services.terminal.adapters.local_process import LocalProcessAdapter


class TermuxAdapter(LocalProcessAdapter):
    """Android/Termux adapter. Same subprocess mechanics as Linux; kept
    distinct because tool installation (pkg vs apt) and available
    executables differ, and future recovery logic needs to branch on it."""

    name = "termux"
