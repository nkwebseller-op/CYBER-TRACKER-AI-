import os

import pytest
from services.terminal.errors import InvalidRequestError, InvalidWorkingDirectoryError
from services.terminal.validation import (
    filter_environment,
    validate_argv,
    validate_working_directory,
)


def test_filter_environment_strips_secret_like_keys():
    filtered = filter_environment(
        {
            "GEMINI_API_KEY": "leaked",
            "AUTH_TOKEN": "leaked",
            "DB_PASSWORD": "leaked",
            "SOME_PRIVATE_KEY": "leaked",
            "SAFE_FLAG": "kept",
        }
    )
    assert filtered == {"SAFE_FLAG": "kept"}


def test_validate_working_directory_accepts_root(tmp_path):
    resolved = validate_working_directory(None, workspace_root=str(tmp_path))
    assert resolved == os.path.realpath(str(tmp_path))


def test_validate_working_directory_accepts_subdirectory(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    resolved = validate_working_directory("sub", workspace_root=str(tmp_path))
    assert resolved == os.path.realpath(str(sub))


def test_validate_working_directory_rejects_traversal(tmp_path):
    with pytest.raises(InvalidWorkingDirectoryError):
        validate_working_directory("../../etc", workspace_root=str(tmp_path))


def test_validate_working_directory_rejects_absolute_path_outside_root(tmp_path):
    with pytest.raises(InvalidWorkingDirectoryError):
        validate_working_directory("/etc", workspace_root=str(tmp_path))


def test_validate_argv_rejects_empty():
    with pytest.raises(InvalidRequestError):
        validate_argv([])


def test_validate_argv_rejects_non_string_args():
    with pytest.raises(InvalidRequestError):
        validate_argv(["echo", 123])


def test_validate_argv_rejects_too_many_args():
    with pytest.raises(InvalidRequestError):
        validate_argv(["echo"] * 100)


def test_validate_argv_accepts_reasonable_command():
    validate_argv(["python3", "-c", "print('ok')"])
