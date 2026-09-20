from services.tools.models import SourceProvenance, SourceType, ToolCandidate
from services.tools.proposal import build_tool_selection_proposal


def _candidate(name="dig") -> ToolCandidate:
    return ToolCandidate(
        name=name,
        display_name=name,
        description="test",
        supported_platforms=("LINUX", "MACOS"),
        dependencies=("libpcap",),
        provenance=SourceProvenance(source_type=SourceType.OFFICIAL_WEBSITE),
    )


def test_proposal_aggregates_platforms_and_dependencies():
    proposal = build_tool_selection_proposal("dns", [_candidate("dig"), _candidate("nslookup")])

    assert set(proposal.expected_platforms) == {"LINUX", "MACOS"}
    assert "libpcap" in proposal.expected_dependencies


def test_proposal_reason_is_factual_not_a_score():
    proposal = build_tool_selection_proposal("dns", [_candidate()])
    assert "dns" in proposal.reason
    assert "score" not in proposal.reason.lower()


def test_proposal_with_no_candidates_says_so():
    proposal = build_tool_selection_proposal("underwater basket weaving", [])
    assert proposal.candidates == []
    assert "No known candidates" in proposal.reason


def test_proposal_to_public_dict_never_includes_raw_object():
    proposal = build_tool_selection_proposal("dns", [_candidate()])
    public = proposal.to_public_dict()
    assert public["candidateNames"] == ["dig"]
    assert "requiredCapability" in public
