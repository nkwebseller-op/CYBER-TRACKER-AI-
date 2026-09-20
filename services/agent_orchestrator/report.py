"""ReportBuilder: assembles the structured hand-off for the existing
reporting system at task completion. Every field is drawn directly from
persisted task state — nothing is invented or inferred beyond what
actually happened."""

from services.agent_orchestrator.models import AgentTaskState, EvidenceKind


class ReportBuilder:
    def build(self, state: AgentTaskState) -> dict:
        verified = [e for e in state.findings if e.kind == EvidenceKind.VERIFIED_FINDING]
        unverified = [e for e in state.findings if e.kind == EvidenceKind.FINDING]
        return {
            "taskId": str(state.id),
            "objective": state.objective,
            "target": state.target,
            "targetType": state.target_type,
            "scope": list(state.scope),
            "authorizationStatus": state.authorization_status,
            "actionsPerformed": [
                {
                    "actionType": a.action_type.value,
                    "tool": a.tool,
                    "resultSummary": a.result_summary,
                    "approvalState": a.approval_state.value,
                }
                for a in state.actions
            ],
            "toolsUsed": list(state.selected_tools),
            "observations": [e.summary for e in state.observations],
            "findings": [e.summary for e in unverified],
            "verifiedFindings": [e.summary for e in verified],
            "evidence": [
                {
                    "id": str(e.id),
                    "kind": e.kind.value,
                    "summary": e.summary,
                    "createdAt": e.created_at.isoformat(),
                }
                for e in state.evidence
            ],
            "verificationStatus": "verified" if verified else "unverified",
            "errors": [{"category": e.category, "message": e.message} for e in state.errors],
            "recoveryAttempts": [
                {"errorCategory": r.error_category, "strategy": r.strategy, "outcome": r.outcome}
                for r in state.recovery_attempts
            ],
            "unresolvedItems": list(state.unknowns),
            "assumptions": list(state.assumptions),
            "recommendations": self._recommendations(state),
            "createdAt": state.created_at.isoformat(),
            "completedAt": state.completed_at.isoformat() if state.completed_at else None,
        }

    @staticmethod
    def _recommendations(state: AgentTaskState) -> list[str]:
        recommendations = []
        if state.unknowns:
            recommendations.append(
                "Additional authorized investigation is needed to resolve remaining unknowns."
            )
        if any(e.kind == EvidenceKind.FINDING for e in state.findings):
            recommendations.append(
                "One or more findings remain unverified — corroborate with an independent check "
                "before acting on them."
            )
        return recommendations
