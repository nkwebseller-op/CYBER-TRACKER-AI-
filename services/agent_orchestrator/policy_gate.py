"""AgentPolicyGate: the mandatory checkpoint between a validated
`AgentDecision` and turning it into an executed `AgentAction`.

    AI decision -> structured action -> AgentPolicyGate (this file)
    -> [PolicyEngine + ToolPolicyGate for anything that reaches an
       OS-level effect] -> ApprovalManager -> ExecutionCoordinator

This gate never grants authorization itself — it only ever narrows what
the orchestrator is willing to attempt:

  1. The task's `authorization_status` must be AUTHORIZED before any
     EXECUTION_ACTION_TYPES action (RUN_DIAGNOSTIC, INSTALL_TOOL) is even
     built — an unauthorized/unknown target stops here, every time,
     regardless of what the model asked for.
  2. A decision naming a target other than the task's own `target` is
     rejected outright (`OutOfScopeError`) — the agent can never expand
     scope by having the model simply mention a different host.
  3. `requires_approval` from the model is never trusted alone — a
     RUN_DIAGNOSTIC/INSTALL_TOOL action requiring approval is *always*
     marked as needing one, whether or not the model said so, and it is
     services.policy.engine.PolicyEngine (via the terminal/installation
     services themselves) that has final say at execution time — this
     gate can only make an action *more* cautious, never less.
"""

from dataclasses import dataclass

from services.agent_orchestrator.actions import EXECUTION_ACTION_TYPES, ActionType
from services.agent_orchestrator.ai_schemas import AgentDecision
from services.agent_orchestrator.errors import OutOfScopeError
from services.agent_orchestrator.models import AgentAction, AgentTaskState, ApprovalState


@dataclass
class GateDecision:
    allowed: bool
    reasons: list[str]
    requires_approval: bool


class AgentPolicyGate:
    def evaluate(self, state: AgentTaskState, decision: AgentDecision) -> GateDecision:
        reasons: list[str] = []

        if decision.action_type in EXECUTION_ACTION_TYPES:
            if state.authorization_status != "AUTHORIZED":
                reasons.append(
                    f"Authorization status is '{state.authorization_status}', not AUTHORIZED — "
                    "an execution action cannot proceed."
                )
                return GateDecision(allowed=False, reasons=reasons, requires_approval=True)

        target_in_arguments = decision.arguments.get("target")
        if (
            target_in_arguments
            and state.target
            and str(target_in_arguments).strip().lower() != state.target.strip().lower()
        ):
            raise OutOfScopeError(
                f"Decision names target '{target_in_arguments}', outside the task's "
                f"authorized target '{state.target}'."
            )

        # Never trust the model's own requiresApproval=False for an
        # execution action — always require it; the model can only ever
        # make this stricter (True), never looser.
        requires_approval = decision.requires_approval or decision.action_type in (
            ActionType.RUN_DIAGNOSTIC,
            ActionType.INSTALL_TOOL,
        )

        reasons.append("Decision is within task scope and authorization is sufficient so far.")
        return GateDecision(allowed=True, reasons=reasons, requires_approval=requires_approval)

    @staticmethod
    def build_action(decision: AgentDecision, gate: GateDecision) -> AgentAction:
        return AgentAction(
            action_type=decision.action_type,
            target=decision.arguments.get("target"),
            capability=decision.required_capability,
            tool=decision.tool,
            parameters=dict(decision.arguments),
            requires_approval=gate.requires_approval,
            approval_state=(
                ApprovalState.PENDING if gate.requires_approval else ApprovalState.NOT_REQUIRED
            ),
            expected_result=decision.next_action,
            verification_requirement="; ".join(decision.verification_plan),
            reasoning_summary=decision.reasoning_summary,
            confidence=decision.confidence,
        )
