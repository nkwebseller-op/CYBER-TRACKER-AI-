from datetime import UTC, datetime

from services.installation.verifier import InstallationVerifier
from services.terminal.models import CommandStatus, TerminalCommandResult
from services.terminal.platform_types import PlatformIdentifier


def _result(status: CommandStatus, exit_code=None, stdout=None) -> TerminalCommandResult:
    return TerminalCommandResult(
        command_id=__import__("uuid").uuid4(),
        session_id=__import__("uuid").uuid4(),
        status=status,
        platform=PlatformIdentifier.LINUX,
        started_at=datetime.now(UTC),
        exit_code=exit_code,
        stdout=stdout,
    )


def test_verified_requires_completed_status_zero_exit_and_output():
    verification = InstallationVerifier().evaluate(
        _result(CommandStatus.COMPLETED, exit_code=0, stdout="dig 9.18")
    )
    assert verification.verified is True
    assert verification.checks["verification_command_completed"] == "PASS"


def test_exit_code_zero_alone_is_not_sufficient_without_output():
    verification = InstallationVerifier().evaluate(
        _result(CommandStatus.COMPLETED, exit_code=0, stdout="")
    )
    assert verification.verified is False
    assert verification.checks["verification_output_present"] == "UNKNOWN"


def test_non_zero_exit_is_not_verified():
    verification = InstallationVerifier().evaluate(
        _result(CommandStatus.FAILED, exit_code=1, stdout="")
    )
    assert verification.verified is False
    assert verification.checks["verification_exit_code_zero"] == "FAIL"


def test_timeout_result_is_never_verified():
    verification = InstallationVerifier().evaluate(_result(CommandStatus.TIMEOUT))
    assert verification.verified is False
    assert verification.checks["verification_command_completed"] == "FAIL"


def test_unknown_exit_code_is_recorded_as_unknown_not_pass():
    verification = InstallationVerifier().evaluate(
        _result(CommandStatus.CANCELLED, exit_code=None)
    )
    assert verification.checks["verification_exit_code_zero"] == "UNKNOWN"
    assert verification.verified is False
