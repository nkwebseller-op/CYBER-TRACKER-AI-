"""Agent memory.

Short-term task memory is just `AgentTaskState` itself (objective, target,
workflow, observations, findings, errors, decisions, completed actions) —
there is no separate short-term store to duplicate, it's exactly what the
orchestrator already persists per task via AgentTaskRegistry.

Long-term memory is a small, explicit key/value store for non-sensitive
user/project preferences (e.g. "preferred report format"). It refuses to
store anything secret-shaped, using the same pattern as
services/terminal/validation.py's `_SECRET_KEY_PATTERN`, and it never
influences authorization — see `LongTermMemoryStore.set`, which is the
only write path and cannot be reached from anywhere that also grants
scope/authorization.
"""

import re
from typing import Protocol

_SECRET_KEY_PATTERN = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY|PRIVATE[_-]?KEY|CREDENTIAL|COOKIE|_KEY$)",
    re.IGNORECASE,
)
_SECRET_VALUE_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


class MemoryRejectedError(ValueError):
    pass


def _reject_if_secret_shaped(key: str, value: str) -> None:
    if _SECRET_KEY_PATTERN.search(key):
        raise MemoryRejectedError(f"Refusing to store secret-shaped key '{key}' in agent memory.")
    if _SECRET_VALUE_PATTERN.search(value):
        raise MemoryRejectedError("Refusing to store a secret-shaped value in agent memory.")


class LongTermMemoryStore(Protocol):
    def get(self, project_id: str, key: str) -> str | None: ...
    def set(self, project_id: str, key: str, value: str) -> None: ...
    def list_keys(self, project_id: str) -> list[str]: ...


class InMemoryLongTermMemoryStore:
    def __init__(self) -> None:
        self._data: dict[tuple[str, str], str] = {}

    def get(self, project_id: str, key: str) -> str | None:
        return self._data.get((project_id, key))

    def set(self, project_id: str, key: str, value: str) -> None:
        _reject_if_secret_shaped(key, value)
        self._data[(project_id, key)] = value

    def list_keys(self, project_id: str) -> list[str]:
        return [k for (pid, k) in self._data if pid == project_id]
