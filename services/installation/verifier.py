"""InstallationVerifier: deterministic post-install checks.

Never reports INSTALLED merely because an install command exited 0 — see
`verify()`, which runs a separate, independent read-only check command
(via the same TerminalEngine pipeline the install step used) and only
confirms success when that check *itself* both exits cleanly and returns
non-empty, parseable output. Anything it cannot confirm is recorded as
UNKNOWN in `checks`, never silently upgraded to a pass.
"""

from services.installation.models import InstallationVerification
from services.terminal.models import CommandStatus, TerminalCommandResult


class InstallationVerifier:
    def evaluate(self, verification_result: TerminalCommandResult) -> InstallationVerification:
        checks: dict[str, str] = {}

        ran_cleanly = verification_result.status == CommandStatus.COMPLETED
        checks["verification_command_completed"] = "PASS" if ran_cleanly else "FAIL"

        exit_ok = verification_result.exit_code == 0
        if exit_ok:
            checks["verification_exit_code_zero"] = "PASS"
        elif verification_result.exit_code is not None:
            checks["verification_exit_code_zero"] = "FAIL"
        else:
            checks["verification_exit_code_zero"] = "UNKNOWN"

        stdout = (verification_result.stdout or "").strip()
        has_output = len(stdout) > 0
        checks["verification_output_present"] = "PASS" if has_output else "UNKNOWN"

        verified = ran_cleanly and exit_ok and has_output
        return InstallationVerification(
            executable_found=verified or (ran_cleanly and exit_ok),
            version_output=stdout or None,
            checks=checks,
            verified=verified,
        )
