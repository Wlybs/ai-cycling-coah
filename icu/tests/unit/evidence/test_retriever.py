"""T76: public retrieve() — top-K + phase bonus + filters."""
from __future__ import annotations

import pytest

from src.coach.evidence.retriever import retrieve
from src.coach.evidence.types import CitationContext, EvidenceCard


def _card(ulid: str, *, tags: list[str], body: str = "",
          phase: list[str] | None = None,
          applies_to: list[str] | None = None,
          contraindications: list[str] | None = None,
          status: str = "active",
          superseded_by: str | None = None):
    return EvidenceCard(
        ulid=ulid,
        title="Test card title for ULID",
        authors=["A"],
        year=2020,
        source="Test 1(2):3-4",
        tags=tags,
        phase=phase or [],
        applies_to=applies_to or [],
        finding="Some finding statement that is at least 20 characters long.",
        dosing_hint="Some dosing hint.",
        contraindications=contraindications or [],
        status=status,
        superseded_by=superseded_by,
        body_md=body,
    )


U1 = "01HXR0NM8K000000000000000A"
U2 = "01HXR0NM8K000000000000000B"
U3 = "01HXR0NM8K000000000000000C"
U4 = "01HXR0NM8K000000000000000D"
U5 = "01HXR0NM8K000000000000000E"


def test_retrieve_empty_corpus():
    ctx = CitationContext(query_terms=["taper"])
    assert retrieve(context=ctx, cards=[]) == []


def test_retrieve_no_query_match_returns_empty():
    cards = [_card(U1, tags=["taper"], body="recovery")]
    ctx = CitationContext(query_terms=["sprint"])
    assert retrieve(context=ctx, cards=cards) == []


def test_retrieve_single_match_normalized_to_one():
    cards = [
        _card(U1, tags=["taper", "peaking"], body="taper recovery"),
        _card(U2, tags=["sprint"], body="other"),
    ]
    ctx = CitationContext(query_terms=["taper"])
    out = retrieve(context=ctx, cards=cards)
    assert len(out) == 1
    assert out[0].card.ulid == U1
    assert out[0].score == pytest.approx(1.0)
    assert "taper" in out[0].matched_terms


def test_retrieve_top_k_truncation():
    cards = [_card(u, tags=["taper"], body=f"taper extra_{i}")
             for i, u in enumerate([U1, U2, U3, U4, U5])]
    ctx = CitationContext(query_terms=["taper"], top_k=2)
    out = retrieve(context=ctx, cards=cards)
    assert len(out) == 2


def test_retrieve_min_score_filter():
    # 2 cards: one strong match, one weak match
    cards = [
        _card(U1, tags=["taper", "peaking"], body="taper taper taper"),
        _card(U2, tags=["other"], body="taper occasionally mentioned"),
    ]
    ctx = CitationContext(query_terms=["taper"], min_score=0.95)
    out = retrieve(context=ctx, cards=cards)
    # Only the strongest (normalized 1.0) survives
    assert len(out) == 1
    assert out[0].card.ulid == U1


def test_retrieve_phase_bonus():
    # Two cards equal raw_score; only one matches phase
    body = "taper recovery"
    cards = [
        _card(U1, tags=["taper"], body=body, phase=["competitive"]),
        _card(U2, tags=["taper"], body=body, phase=["base"]),
    ]
    ctx = CitationContext(query_terms=["taper"], phase="competitive")
    out = retrieve(context=ctx, cards=cards)
    # U1 (matches phase) should rank first
    assert out[0].card.ulid == U1


def test_retrieve_contraindication_excludes_card():
    cards = [
        _card(U1, tags=["taper"], body="taper", contraindications=["acute_illness"]),
        _card(U2, tags=["taper"], body="taper"),
    ]
    ctx = CitationContext(query_terms=["taper"],
                          contraindications_present=["acute_illness"])
    out = retrieve(context=ctx, cards=cards)
    assert {r.card.ulid for r in out} == {U2}


def test_retrieve_excludes_deprecated():
    cards = [
        _card(U1, tags=["taper"], body="taper",
              status="deprecated", superseded_by=U2),
        _card(U2, tags=["taper"], body="taper"),
    ]
    ctx = CitationContext(query_terms=["taper"])
    out = retrieve(context=ctx, cards=cards)
    assert {r.card.ulid for r in out} == {U2}


def test_retrieve_deterministic_tie_break_by_ulid():
    # Two identical cards with different ULIDs → U1 should come first (lex asc)
    body = "taper recovery"
    cards = [
        _card(U2, tags=["taper"], body=body),
        _card(U1, tags=["taper"], body=body),
    ]
    ctx = CitationContext(query_terms=["taper"])
    out = retrieve(context=ctx, cards=cards)
    assert [r.card.ulid for r in out] == [U1, U2]
