"""T77: render_references_section markdown output."""
from __future__ import annotations

from src.coach.evidence.prompt_section import render_references_section
from src.coach.evidence.types import EvidenceCard, RetrievedCard


U1 = "01HXR0NM8K000000000000000A"
U2 = "01HXR0NM8K000000000000000B"
U3 = "01HXR0NM8K000000000000000C"


def _card(ulid: str, *, title: str = "Test card title for citation") -> EvidenceCard:
    return EvidenceCard(
        ulid=ulid,
        title=title,
        authors=["Author A"],
        year=2020,
        source="Test 1(2):3-4",
        tags=["taper"],
        phase=[],
        applies_to=[],
        finding="Some finding statement that is at least 20 characters long.",
        dosing_hint="Some dosing hint here.",
        contraindications=[],
        status="active",
        superseded_by=None,
        body_md="taper recovery polarized",
    )


def test_render_empty_returns_none_applicable_marker():
    md = render_references_section([])
    assert "## References" in md
    assert "(none directly applicable" in md


def test_render_single_card_contains_all_fields():
    rc = RetrievedCard(card=_card(U1), score=0.87, matched_terms=["taper"])
    md = render_references_section([rc])
    assert "## References" in md
    assert f"**[{U1}]" in md
    assert "Test card title for citation" in md
    assert "(score 0.870)" in md
    assert "matched: taper" in md
    assert "finding:" in md
    assert "dosing_hint:" in md


def test_render_three_cards_numbered_in_order():
    rcs = [
        RetrievedCard(card=_card(U1), score=1.000, matched_terms=["taper"]),
        RetrievedCard(card=_card(U2), score=0.700, matched_terms=["recovery"]),
        RetrievedCard(card=_card(U3), score=0.500, matched_terms=["polarized"]),
    ]
    md = render_references_section(rcs)
    pos1 = md.find(f"1. **[{U1}]")
    pos2 = md.find(f"2. **[{U2}]")
    pos3 = md.find(f"3. **[{U3}]")
    assert 0 < pos1 < pos2 < pos3, f"order broken: {pos1=} {pos2=} {pos3=}"


def test_render_card_with_empty_matched_terms_uses_safe_marker():
    rc = RetrievedCard(card=_card(U1), score=0.42, matched_terms=[])
    md = render_references_section([rc])
    assert "matched: (none)" in md
