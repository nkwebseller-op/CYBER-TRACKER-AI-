import pytest
from services.agent_orchestrator.memory import InMemoryLongTermMemoryStore, MemoryRejectedError


def test_set_and_get_roundtrip():
    store = InMemoryLongTermMemoryStore()
    store.set("project-1", "preferred_report_format", "pdf")
    assert store.get("project-1", "preferred_report_format") == "pdf"


def test_rejects_secret_shaped_key():
    store = InMemoryLongTermMemoryStore()
    with pytest.raises(MemoryRejectedError):
        store.set("project-1", "api_key", "irrelevant-value")


def test_rejects_password_key():
    store = InMemoryLongTermMemoryStore()
    with pytest.raises(MemoryRejectedError):
        store.set("project-1", "user_password", "irrelevant")


def test_rejects_secret_shaped_value_even_with_safe_key():
    store = InMemoryLongTermMemoryStore()
    with pytest.raises(MemoryRejectedError):
        store.set("project-1", "notes", "AKIAABCDEFGHIJKLMNOP")


def test_list_keys_scoped_per_project():
    store = InMemoryLongTermMemoryStore()
    store.set("project-1", "a", "1")
    store.set("project-2", "b", "2")
    assert store.list_keys("project-1") == ["a"]


def test_get_missing_key_returns_none():
    store = InMemoryLongTermMemoryStore()
    assert store.get("project-1", "missing") is None
