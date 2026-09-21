"""Unit tests for the Termux connector's on-device validation. These
are the hard, connector-side defences against a compromised or hostile
backend — they run regardless of what the server sends."""

import sys
from pathlib import Path

# Import the connector module directly (it's a single script, not a
# package, so we path-hack rather than install it).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cyberai_termux as connector  # noqa: E402


import pytest  # noqa: E402


def test_argv_must_be_non_empty_list():
    with pytest.raises(connector.RefusedError):
        connector._validate_argv(None)
    with pytest.raises(connector.RefusedError):
        connector._validate_argv([])
    with pytest.raises(connector.RefusedError):
        connector._validate_argv("echo hi")


def test_argv_rejects_nul_byte():
    with pytest.raises(connector.RefusedError):
        connector._validate_argv(["echo", "hi\x00"])


def test_argv_rejects_shell_metacharacters_in_first_element():
    with pytest.raises(connector.RefusedError):
        connector._validate_argv(["echo; rm -rf /"])


def test_argv_allows_metacharacters_in_data_arguments():
    argv = connector._validate_argv(["echo", "; not a real shell command"])
    assert argv[1].startswith("; not")


def test_argv_length_limit_enforced():
    with pytest.raises(connector.RefusedError):
        connector._validate_argv(["cmd"] + ["arg"] * 200)


def test_env_overrides_reject_secret_shaped_keys():
    with pytest.raises(connector.RefusedError):
        connector._validate_env_overrides({"MY_API_KEY": "irrelevant"})
    with pytest.raises(connector.RefusedError):
        connector._validate_env_overrides({"user_password": "irrelevant"})


def test_env_overrides_accept_normal_keys():
    result = connector._validate_env_overrides({"LANG": "en_US.UTF-8"})
    assert result == {"LANG": "en_US.UTF-8"}


def test_env_overrides_reject_non_string():
    with pytest.raises(connector.RefusedError):
        connector._validate_env_overrides({"KEY": 123})


def test_working_directory_must_be_under_allowed_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(connector, "DEFAULT_ALLOWED_ROOTS", [str(tmp_path)])
    # In-scope
    subdir = tmp_path / "work"
    subdir.mkdir()
    assert connector._validate_working_directory(str(subdir)) == str(subdir)
    # Out of scope
    with pytest.raises(connector.RefusedError):
        connector._validate_working_directory("/etc")


def test_working_directory_none_is_allowed():
    assert connector._validate_working_directory(None) is None


def test_timeout_clamps_to_maximum():
    assert connector._validate_timeout(99999) == float(connector.MAX_TIMEOUT_SECONDS)


def test_timeout_rejects_non_positive():
    with pytest.raises(connector.RefusedError):
        connector._validate_timeout(-1)
    with pytest.raises(connector.RefusedError):
        connector._validate_timeout("30")


def test_token_file_must_be_mode_0600(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("supersecret")
    token_file.chmod(0o644)  # too permissive
    with pytest.raises(SystemExit) as excinfo:
        connector._read_token_file(str(token_file))
    assert "permissive" in str(excinfo.value).lower()


def test_token_file_reads_correctly_with_mode_0600(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("supersecret\n")
    token_file.chmod(0o600)
    assert connector._read_token_file(str(token_file)) == "supersecret"


def test_empty_token_file_is_rejected(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("")
    token_file.chmod(0o600)
    with pytest.raises(SystemExit):
        connector._read_token_file(str(token_file))


def test_missing_token_file_is_rejected(tmp_path):
    with pytest.raises(SystemExit):
        connector._read_token_file(str(tmp_path / "missing"))
