"""T75: internal TF-IDF helpers — _build_idf + _raw_score."""
from __future__ import annotations

import math

import pytest

from src.coach.evidence.retriever import _build_idf, _card_search_terms, _raw_score
from src.coach.evidence.types import EvidenceCard


def _card(ulid: str, *, tags: list[str], body: str = ""):
    return EvidenceCard(
        ulid=ulid,
        title="Test card title for ULID",
        authors=["A"],
        year=2020,
        source="Test 1(2):3-4",
        tags=tags,
        phase=[],
        applies_to=[],
        finding="Some finding statement that is at least 20 characters long.",
        dosing_hint="Some dosing hint.",
        contraindications=[],
        status="active",
        superseded_by=None,
        body_md=body,
    )


ULID_1 = "01HXR0NM8K000000000000000A"
ULID_2 = "01HXR0NM8K000000000000000B"
ULID_3 = "01HXR0NM8K000000000000000C"


def test_build_idf_empty_returns_empty():
    assert _build_idf([]) == {}


def test_build_idf_single_card_smoothed_value():
    # Smoothed IDF: log((N+1)/(df+1)) + 1; N=1 df=1 → log(2/2)+1 = 1.0
    card = _card(ULID_1, tags=["taper"], body="recovery")
    idf = _build_idf([card])
    assert "taper" in idf and "recovery" in idf
    assert idf["taper"] == pytest.approx(math.log(2 / 2) + 1.0, rel=1e-6)
    assert idf["taper"] == pytest.approx(1.0, rel=1e-6)


def test_build_idf_rare_token_higher_than_common():
    # 3 cards: "common" appears in all 3, "rare" appears in 1
    c1 = _card(ULID_1, tags=["common"], body="rare unique")
    c2 = _card(ULID_2, tags=["common"], body="other words")
    c3 = _card(ULID_3, tags=["common"], body="more text")
    idf = _build_idf([c1, c2, c3])
    assert idf["rare"] > idf["common"]


def test_card_search_terms_concat_tags_body_and_phase():
    card = EvidenceCard(
        ulid=ULID_1,
        title="Test card title for ULID",
        authors=["A"], year=2020, source="Test 1(2):3-4",
        tags=["taper", "peaking"], phase=["competitive", "transition"],
        applies_to=[],
        finding="Some finding statement that is at least 20 characters long.",
        dosing_hint="Some dosing hint.",
        contraindications=[], status="active", superseded_by=None,
        body_md="recovery taper",
    )
    terms = _card_search_terms(card)
    # tags first, then body, then phase (so phase metadata participates in TF-IDF)
    assert terms[:2] == ["taper", "peaking"]
    assert "recovery" in terms
    assert "competitive" in terms
    assert "transition" in terms


def test_raw_score_no_match_returns_zero_and_empty_matched():
    card = _card(ULID_1, tags=["taper"], body="recovery")
    idf = _build_idf([card])
    score, matched = _raw_score(["sprint"], card, idf)
    assert score == 0.0
    assert matched == []


def test_raw_score_two_matched_terms_returns_positive_and_lists_them():
    c1 = _card(ULID_1, tags=["taper"], body="recovery polarized")
    c2 = _card(ULID_2, tags=["sprint"], body="other content")
    idf = _build_idf([c1, c2])
    score, matched = _raw_score(["taper", "polarized"], c1, idf)
    assert score > 0
    assert set(matched) == {"taper", "polarized"}


def test_raw_score_deterministic_repeat_calls():
    c1 = _card(ULID_1, tags=["taper"], body="recovery polarized peaking")
    c2 = _card(ULID_2, tags=["sprint"], body="other content here")
    idf = _build_idf([c1, c2])
    a = _raw_score(["taper", "recovery"], c1, idf)
    b = _raw_score(["taper", "recovery"], c1, idf)
    assert a == b
