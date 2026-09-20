"""Execution Controller.

The only way to obtain an `ApprovedExecution` is via `from_policy_decision`,
which requires a `PolicyDecision` whose verdict is `ALLOW` (or
`REQUIRE_APPROVAL` that has since been explicitly approved). Terminal
adapters' `execute()` accepts nothing else. This is what makes "AI never has
a direct path to a shell" true in code, not just in the docs.
"""

from dataclasses import dataclass
from uuid import UUID

from services.policy.engine import PolicyDecision, PolicyVerdict
from services.terminal.adapters.base import CommandSpec, TerminalAdapter
from services.terminal.platform_select import select_adapter


class ExecutionNotApprovedError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApprovedExecution:
    action_id: UUID
    command: CommandSpec

    @classmethod
    def from_policy_decision(
        cls,
        action_id: UUID,
        command: CommandSpec,
        decision: PolicyDecision,
        *,
        approved_by_user: bool = False,
    ) -> "ApprovedExecution":
        if decision.verdict == PolicyVerdict.ALLOW:
            return cls(action_id=action_id, command=command)
        if decision.verdict == PolicyVerdict.REQUIRE_APPROVAL and approved_by_user:
            return cls(action_id=action_id, command=command)
        raise ExecutionNotApprovedError(
            f"Action {action_id} is not approved for execution (verdict={decision.verdict!r})."
        )


class ExecutionController:
    def __init__(self, adapter: TerminalAdapter | None = None) -> None:
        self._adapter = adapter or select_adapter()

    async def execute(self, approved: ApprovedExecution):
        return await self._adapter.run(approved.command)
