"""Vetted command templates keyed by action type.

This is the only place argv is ever produced for a real execution. The AI
never sends shell text that reaches a process — it can only request an
`action_type`, which is looked up here *after* the Policy Engine has
already ALLOWed it (see services/terminal/engine.py). If an action type
has no template here, execution is refused — there is no fallback to
"run whatever the caller sent."

Deliberately tiny in this phase: one harmless, cross-platform diagnostic
command so the full pipeline (policy -> engine -> adapter -> result) can
be exercised end-to-end without any real tool being registered yet. Real
templates arrive with services/tools in a later phase.
"""

import sys
from collections.abc import Callable

from services.policy.engine import RiskTier

CommandTemplate = Callable[[], list[str]]


def _diagnostics_echo_test() -> list[str]:
    # Uses the running interpreter itself rather than a shell builtin like
    # `echo`, which isn't a real executable on every platform (notably
    # Windows) — this keeps the template genuinely cross-platform without
    # any per-OS branching.
    return [sys.executable, "-c", "print('cyberai-terminal-engine-ok')"]


COMMAND_TEMPLATES: dict[str, CommandTemplate] = {
    "diagnostics.echo_test": _diagnostics_echo_test,
}

# The server decides an action type's risk tier — a client-supplied risk
# level is never trusted for policy evaluation (see
# apps/api/app/api/routes/terminal.py).
ACTION_RISK_TIERS: dict[str, RiskTier] = {
    "diagnostics.echo_test": RiskTier.LOW,
}


def resolve_command(action_type: str) -> list[str] | None:
    template = COMMAND_TEMPLATES.get(action_type)
    return template() if template else None
