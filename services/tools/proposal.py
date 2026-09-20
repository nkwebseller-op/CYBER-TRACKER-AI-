"""AI tool-selection proposal shape.

The AI provider abstraction (services/agent/providers/*) already exists
for chat; this module defines the structured, inspectable shape a
provider's tool-selection output must take — it does not add a new AI
integration, and it never lets a provider's output become an install/run
action. `ToolSelectionProposal` is built from already-discovered
`ToolCandidate`s (see services/tools/discovery.py); nothing here calls a
provider directly, so this stays decoupled from Gemini/mock/whatever
provider services/agent is configured with — a later phase can have the
chat pipeline construct one of these from a provider's structured output
without this module changing.

Every field the phase spec asks for maps directly: required capability,
candidate tools, selection reason, expected platform, expected
dependencies, risk level, verification requirements. The AI never
supplies an entrypoint, argv, or install command here — those don't exist
on a `ToolCandidate` at all.
"""

from dataclasses import dataclass, field

from services.tools.models import ToolCandidate


@dataclass
class ToolSelectionProposal:
    required_capability: str
    candidates: list[ToolCandidate] = field(default_factory=list)
    reason: str = ""
    expected_platforms: tuple[str, ...] = ()
    expected_dependencies: tuple[str, ...] = ()
    verification_requirements: tuple[str, ...] = ()

    def to_public_dict(self) -> dict:
        return {
            "requiredCapability": self.required_capability,
            "reason": self.reason,
            "expectedPlatforms": list(self.expected_platforms),
            "expectedDependencies": list(self.expected_dependencies),
            "verificationRequirements": list(self.verification_requirements),
            "candidateNames": [c.name for c in self.candidates],
        }


def build_tool_selection_proposal(
    capability: str, candidates: list[ToolCandidate]
) -> ToolSelectionProposal:
    """Packages already-discovered candidates into a proposal a chat
    response or approval UI can render. This is deliberately a pure,
    non-AI function in this phase — see module docstring for why the
    actual LLM call (if any) belongs to services/agent, not here, and why
    that's fine: the proposal shape is what matters for keeping the AI's
    output inspectable and non-executable, not which component built it."""
    platforms: set[str] = set()
    dependencies: set[str] = set()
    for candidate in candidates:
        platforms.update(candidate.supported_platforms)
        dependencies.update(candidate.dependencies)

    reason = (
        f"Found {len(candidates)} candidate(s) declaring capabilities relevant to "
        f"'{capability}'."
        if candidates
        else f"No known candidates declare a capability matching '{capability}'."
    )
    return ToolSelectionProposal(
        required_capability=capability,
        candidates=candidates,
        reason=reason,
        expected_platforms=tuple(sorted(platforms)),
        expected_dependencies=tuple(sorted(dependencies)),
        verification_requirements=(
            "source_provenance",
            "license",
            "platform_compatibility",
            "security_policy_review",
        ),
    )
