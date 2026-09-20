"""Tool research abstraction.

`ToolResearchProvider` is deliberately narrow: `search(capability)` returns
structured `ToolCandidate`s, never a raw URL the caller is expected to
fetch-and-run, and never a binary. This phase ships one concrete
provider — `CuratedToolResearchProvider`, a small, hand-maintained list of
well-known, genuinely official-source tools per capability — instead of
live GitHub/web crawling. That keeps discovery fully offline and
deterministic for tests and CI while the interface it implements is the
same one a real web/GitHub-backed provider would implement later.

`GitHubToolResearchProvider` is declared as the documented extension
point for that later phase and intentionally raises `NotImplementedError`
— building unrestricted internet research is explicitly out of scope for
Phase 10 (see the phase's "Do NOT yet implement unrestricted autonomous
internet downloading" requirement).
"""

from typing import Protocol

from services.policy.engine import RiskTier
from services.tools.models import SourceProvenance, SourceType, ToolCandidate, ToolCategory


class ToolResearchProvider(Protocol):
    async def search(self, capability: str) -> list[ToolCandidate]: ...


# A small, hand-curated set of well-known tools with genuinely official
# provenance, keyed by lowercase capability keyword. Not exhaustive — this
# is a seed for the discovery pipeline and future real research providers,
# not a claim of completeness.
_CURATED_CATALOG: dict[str, list[dict]] = {
    "dns": [
        {
            "name": "dig",
            "display_name": "dig (dnsutils/bind-utils)",
            "description": "Standard DNS lookup utility for querying DNS servers.",
            "category": ToolCategory.DNS_DOMAIN_ANALYSIS,
            "capabilities": ("dns_lookup", "dns_trace"),
            "supported_platforms": ("LINUX", "MACOS"),
            "provenance": SourceProvenance(
                source_type=SourceType.OFFICIAL_WEBSITE,
                source_url="https://www.isc.org/bind/",
                documentation_url="https://bind9.readthedocs.io/",
                publisher="Internet Systems Consortium (ISC)",
            ),
            "license": "MPL-2.0",
            "installation_method": "OS package manager (apt/dnf/brew)",
            "risk_level": RiskTier.LOW,
        },
    ],
    "network": [
        {
            "name": "nmap",
            "display_name": "Nmap",
            "description": "Network discovery and security auditing utility.",
            "category": ToolCategory.NETWORK_DIAGNOSTICS,
            "capabilities": ("port_scan", "host_discovery", "service_detection"),
            "supported_platforms": ("LINUX", "MACOS", "WINDOWS"),
            "provenance": SourceProvenance(
                source_type=SourceType.OFFICIAL_WEBSITE,
                source_url="https://nmap.org/",
                repository_url="https://github.com/nmap/nmap",
                documentation_url="https://nmap.org/book/man.html",
                publisher="Nmap Project",
            ),
            "license": "NPSL (Nmap Public Source License)",
            "installation_method": "OS package manager / official installer",
            "risk_level": RiskTier.MEDIUM,
        },
    ],
    "web": [
        {
            "name": "curl",
            "display_name": "curl",
            "description": "Command-line tool for transferring data with URLs.",
            "category": ToolCategory.WEB_API_TESTING,
            "capabilities": ("http_request", "api_testing"),
            "supported_platforms": ("LINUX", "MACOS", "WINDOWS"),
            "provenance": SourceProvenance(
                source_type=SourceType.OFFICIAL_WEBSITE,
                source_url="https://curl.se/",
                repository_url="https://github.com/curl/curl",
                documentation_url="https://curl.se/docs/",
                publisher="curl project (Daniel Stenberg et al.)",
            ),
            "license": "MIT-style (curl license)",
            "installation_method": "Bundled with most OSes / package manager",
            "risk_level": RiskTier.LOW,
        },
    ],
}


class CuratedToolResearchProvider:
    """Deterministic, offline, hand-curated catalog. Matches a requested
    capability keyword against the catalog's keys and each candidate's
    declared capabilities/description — no network access, ever."""

    async def search(self, capability: str) -> list[ToolCandidate]:
        needle = capability.strip().lower()
        candidates: list[ToolCandidate] = []
        for keyword, entries in _CURATED_CATALOG.items():
            if needle and needle not in keyword and keyword not in needle:
                # Still allow a match via capability/description text below.
                pass
            for entry in entries:
                haystack = " ".join(
                    [entry["name"], entry["description"], *entry["capabilities"], keyword]
                ).lower()
                if not needle or needle in haystack or keyword in needle:
                    candidates.append(
                        ToolCandidate(
                            name=entry["name"],
                            display_name=entry["display_name"],
                            description=entry["description"],
                            category=entry["category"],
                            capabilities=entry["capabilities"],
                            supported_platforms=entry["supported_platforms"],
                            provenance=entry["provenance"],
                            license=entry["license"],
                            installation_method=entry["installation_method"],
                            risk_level=entry["risk_level"],
                            capability_requested=capability,
                            selection_rationale=(
                                f"Declares capabilities {entry['capabilities']} matching "
                                f"the requested capability '{capability}'; sourced from "
                                f"{entry['provenance'].source_type.value} "
                                f"({entry['provenance'].source_url})."
                            ),
                        )
                    )
        # De-duplicate by name (a candidate can match more than one keyword
        # bucket) while preserving first-seen order.
        seen: set[str] = set()
        unique: list[ToolCandidate] = []
        for candidate in candidates:
            if candidate.name in seen:
                continue
            seen.add(candidate.name)
            unique.append(candidate)
        return unique


class GitHubToolResearchProvider:
    """Documented extension point for a real GitHub/web-backed research
    provider. Deliberately unimplemented in this phase — see module
    docstring. A future implementation must still return `ToolCandidate`s
    with real `SourceProvenance` (never an unverified download mirror
    treated as trusted) and must not make any candidate directly
    executable."""

    async def search(self, capability: str) -> list[ToolCandidate]:
        raise NotImplementedError(
            "Live GitHub/web tool research is not implemented in this phase. "
            "Use CuratedToolResearchProvider, or a test double implementing "
            "ToolResearchProvider."
        )
