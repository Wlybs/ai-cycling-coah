"""T73: EvidenceCard + CitationContext + RetrievedCard schemas (Pydantic v2)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.coach.evidence.types import (
    CitationContext,
    EvidenceCard,
    RetrievedCard,
)


# Fixed valid ULIDs (Crockford base32, 26 chars, no I/L/O/U)
ULID_A = "01HXR0NM8K1234567890ABCDEF"
ULID_B = "01HXR0NM8K1234567890ABCDEG"


def _card_kwargs(**overrides):
    base = dict(
        ulid=ULID_A,
        title="Mujika Padilla 2003 Taper meta-analysis",
        authors=["Mujika I", "Padilla S"],
        year=2003,
        source="Med Sci Sports Exerc 35(7):1182-7",
        tags=["taper", "peaking"],
        phase=["competitive"],
        applies_to=[],
        finding="Volume reduction of 41-60% with intensity preserved is optimal across 7-21d taper.",
        dosing_hint="Reduce volume ~50%, keep intervals.",
        contraindications=[],
        status="active",
        superseded_by=None,
        body_md="# Body\nFull text here, with several keywords like taper, polarized, recovery.",
    )
    base.update(overrides)
    return base


# ---------- EvidenceCard ----------

def test_evidence_card_happy_path_roundtrip():
    card = EvidenceCard(**_card_kwargs())
    js = card.model_dump_json()
    loaded = EvidenceCard.model_validate_json(js)
    assert loaded == card


def test_evidence_card_rejects_lowercase_ulid():
    with pytest.raises(ValidationError):
        EvidenceCard(**_card_kwargs(ulid="01hxr0nm8k1234567890abcdef"))


def test_evidence_card_rejects_short_ulid():
    with pytest.raises(ValidationError):
        EvidenceCard(**_card_kwargs(ulid="01HXR0NM8K"))


def test_evidence_card_rejects_non_snake_case_tag():
    with pytest.raises(ValidationError):
        EvidenceCard(**_card_kwargs(tags=["Taper"]))  # capital
    with pytest.raises(ValidationError):
        EvidenceCard(**_card_kwargs(tags=["taper-x"]))  # hyphen


def test_evidence_card_rejects_unknown_phase():
    with pytest.raises(ValidationError):
        EvidenceCard(**_card_kwargs(phase=["sprint_special"]))


def test_evidence_card_active_must_have_null_superseded_by():
    with pytest.raises(ValidationError):
        EvidenceCard(**_card_kwargs(status="active", superseded_by=ULID_B))


def test_evidence_card_deprecated_must_have_superseded_by():
    with pytest.raises(ValidationError):
        EvidenceCard(**_card_kwargs(status="deprecated", superseded_by=None))
    # happy: deprecated + superseded_by set
    EvidenceCard(**_card_kwargs(status="deprecated", superseded_by=ULID_B))


def test_evidence_card_body_tokens_lowercase_and_unique():
    card = EvidenceCard(**_card_kwargs(
        body_md="Taper Polarized RECOVERY taper recovery."))
    tokens = card.body_tokens
    assert "taper" in tokens
    assert "polarized" in tokens
    assert "recovery" in tokens
    # No uppercase leak
    assert not any(t != t.lower() for t in tokens)


# ---------- CitationContext ----------

def test_citation_context_top_k_bounds():
    CitationContext(query_terms=["taper"], top_k=1)
    CitationContext(query_terms=["taper"], top_k=10)
    with pytest.raises(ValidationError):
        CitationContext(query_terms=["taper"], top_k=0)
    with pytest.raises(ValidationError):
        CitationContext(query_terms=["taper"], top_k=11)


def test_citation_context_requires_non_empty_query_terms():
    with pytest.raises(ValidationError):
        CitationContext(query_terms=[])


def test_citation_context_min_score_range():
    CitationContext(query_terms=["taper"], min_score=0.0)
    CitationContext(query_terms=["taper"], min_score=1.0)
    with pytest.raises(ValidationError):
        CitationContext(query_terms=["taper"], min_score=-0.01)
    with pytest.raises(ValidationError):
        CitationContext(query_terms=["taper"], min_score=1.01)


# ---------- RetrievedCard ----------

def test_retrieved_card_frozen():
    card = EvidenceCard(**_card_kwargs())
    rc = RetrievedCard(card=card, score=0.42, matched_terms=["taper"])
    with pytest.raises(ValidationError):
        rc.score = 0.99  # frozen


def test_retrieved_card_score_non_negative():
    card = EvidenceCard(**_card_kwargs())
    with pytest.raises(ValidationError):
        RetrievedCard(card=card, score=-0.01, matched_terms=[])
