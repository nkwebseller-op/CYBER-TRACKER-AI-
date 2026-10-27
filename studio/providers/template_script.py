from __future__ import annotations

import re

from ..models import Scene, Script, Tone

_WORDS_PER_SECOND = 2.5

_HOOKS: dict[str, str] = {
    "energetic": "Stop scrolling!",
    "professional": "Here is what you need to know.",
    "friendly": "Hey, quick question for you.",
    "luxury": "Introducing something extraordinary.",
}
_STYLES: dict[str, str] = {
    "energetic": "fast, vibrant, dynamic camera movement",
    "professional": "clean, polished, steady corporate look",
    "friendly": "warm, natural light, approachable",
    "luxury": "elegant, slow cinematic motion, premium feel",
}
_CTAS: dict[str, str] = {
    "energetic": "Grab yours today!",
    "professional": "Get started today.",
    "friendly": "Give it a try, you will love it.",
    "luxury": "Experience it for yourself.",
}


def _split_brief(brief: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+|;", brief) if p.strip()]
    out: list[str] = []
    for part in parts:
        # Break very long sentences on commas so each scene stays short enough to read.
        if len(part.split()) > 14:
            out.extend(c.strip() for c in part.split(",") if c.strip())
        else:
            out.append(part)
    return out


class TemplateScriptWriter:
    """Deterministic offline writer: hook, one scene per point in the brief, then a call to action.

    It does not invent claims. Swap in an LLM-backed ScriptWriter for creative copy.
    """

    async def write(self, brief: str, tone: Tone, duration_s: int) -> Script:
        points = _split_brief(brief)
        budget_words = int(duration_s * _WORDS_PER_SECOND)
        subject = (points[0] if points else brief).rstrip(".!? ")

        def visual(focus: str) -> str:
            return (
                f"Commercial video shot about: {subject}. Focus: {focus.rstrip('.!?')}. "
                f"Style: {_STYLES[tone]}. No on-screen text, no logos."
            )

        scenes = [Scene(caption=_HOOKS[tone], narration=_HOOKS[tone], visual=visual(subject))]
        used = len(scenes[0].narration.split()) + len(_CTAS[tone].split())
        for point in points:
            words = len(point.split())
            if used + words > budget_words and len(scenes) > 1:
                break
            scenes.append(Scene(caption=point.rstrip(".!?"), narration=point, visual=visual(point)))
            used += words
        scenes.append(Scene(caption=_CTAS[tone], narration=_CTAS[tone], visual=visual(subject)))
        title = subject[:60]
        return Script(title=title, scenes=scenes)
