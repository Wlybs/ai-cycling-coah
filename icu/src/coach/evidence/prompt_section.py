"""Phase 4 Evidence — markdown rendering for the References section."""
from __future__ import annotations

from src.coach.evidence.types import RetrievedCard


_HEADER = "## References (auto-retrieved by Phase 4 evidence retriever)"
_EMPTY_MARKER = "(none directly applicable for this context)"


def _render_one(idx: int, rc: RetrievedCard) -> str:
    matched = ", ".join(rc.matched_terms) if rc.matched_terms else "(none)"
    return (
        f"{idx}. **[{rc.card.ulid}] {rc.card.title}** (score {rc.score:.3f})\n"
        f"   - matched: {matched}\n"
        f"   - finding: {rc.card.finding}\n"
        f"   - dosing_hint: {rc.card.dosing_hint}\n"
    )


def render_references_section(retrieved: list[RetrievedCard]) -> str:
    """Markdown References block to append to a council/strict prompt body."""
    if not retrieved:
        return f"\n\n{_HEADER}\n\n{_EMPTY_MARKER}\n"
    items = "\n".join(_render_one(i + 1, rc) for i, rc in enumerate(retrieved))
    return f"\n\n{_HEADER}\n\n{items}"
