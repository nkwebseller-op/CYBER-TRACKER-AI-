"""ResultAnalyzer + VerificationEngine.

Turns a raw execution/tool result into `Evidence` with an honest
`EvidenceKind` — an OBSERVATION never silently becomes a FACT, and a
FINDING never silently becomes a VERIFIED_FINDING. "The command exited 0"
is never treated as "the objective is verified" (see `VerificationEngine
.verify`, which requires a second, independent signal — the exact same
principle services/installation/verifier.py already applies to tool
installs).
"""

from services.agent_orchestrator.models import Evidence, EvidenceKind


class ResultAnalyzer:
    def observe(self, *, action_id, summary: str) -> Evidence:
        """A plain OBSERVATION: something the system saw, not yet
        interpreted as meaningful."""
        return Evidence(kind=EvidenceKind.OBSERVATION, summary=summary, source_action_id=action_id)

    def propose_finding(self, *, action_id, summary: str) -> Evidence:
        """An unverified FINDING — a candidate conclusion drawn from one
        observation. Never presented as confirmed."""
        return Evidence(kind=EvidenceKind.FINDING, summary=summary, source_action_id=action_id)

    def assume(self, *, action_id, summary: str) -> Evidence:
        return Evidence(kind=EvidenceKind.ASSUMPTION, summary=summary, source_action_id=action_id)


class VerificationEngine:
    def verify(
        self, finding: Evidence, *, corroborating_evidence: list[str]
    ) -> Evidence:
        """Promotes a FINDING to VERIFIED_FINDING only when at least one
        independent, factual piece of corroborating evidence is supplied
        — never on the strength of the original observation alone."""
        if finding.kind != EvidenceKind.FINDING:
            raise ValueError("Only a FINDING can be verified.")
        if not corroborating_evidence:
            return finding  # stays a FINDING — not verified, and that's reported honestly
        return Evidence(
            id=finding.id,
            kind=EvidenceKind.VERIFIED_FINDING,
            summary=finding.summary + " | verified by: " + "; ".join(corroborating_evidence),
            source_action_id=finding.source_action_id,
        )
