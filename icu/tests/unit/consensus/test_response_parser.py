"""Unit tests for ResponseParser: happy path + 6 hard-rule rejections."""
from __future__ import annotations

import pytest

from src.coach.consensus.response_parser import parse
from src.coach.consensus.types import (
    ConsensusValidationError,
    CouncilVerdict,
)


# ---------- happy ----------

def test_parse_happy_path_returns_council_verdict(happy_response):
    cv = parse(happy_response, mode="council")
    assert isinstance(cv, CouncilVerdict)
    assert cv.mode == "council"
    assert cv.verdict == "REVISE"
    assert cv.confidence == pytest.approx(0.72)
    assert {t.role for t in cv.expert_turns} == {
        "planner", "critic", "physiologist", "arbiter"
    }
    # Critic cited_data: parser must surface ≥3 atomic data references
    critic = next(t for t in cv.expert_turns if t.role == "critic")
    assert len(critic.cited_data) >= 3
    # summary_json passthrough preserved
    assert cv.summary_json["changes"][0]["day"] == "Tue"


def test_parse_happy_path_sets_justification_from_arbiter(happy_response):
    cv = parse(happy_response, mode="council")
    assert "REVISE" in cv.justification or cv.justification.strip() != ""


# ---------- 6 rejection modes ----------

@pytest.mark.parametrize(
    "fname,expected_violation_substr",
    [
        ("reject_no_critic.md",         "section.missing.critic"),
        ("reject_critic_2_points.md",   "critic.points<3"),
        ("reject_critic_no_data.md",    "critic.point_no_data"),
        ("reject_phys_2_keywords.md",   "physiologist.keywords<3"),
        ("reject_bad_verdict.md",       "verdict.invalid"),
        ("reject_no_summary_json.md",   "summary_json.missing"),
    ],
)
def test_parse_rejects_each_hard_rule_breach(reject_responses, fname,
                                             expected_violation_substr):
    text = reject_responses[fname]
    with pytest.raises(ConsensusValidationError) as excinfo:
        parse(text, mode="council")
    found = excinfo.value.violations
    assert any(expected_violation_substr in v for v in found), (
        f"expected violation containing {expected_violation_substr!r}, "
        f"got {found}"
    )


def test_parse_strict_mode_accepts_concatenated_responses(happy_response):
    """strict 模式：调用方把 4 份独立 response 拼成单一文档传入；parser 依旧合法。"""
    cv = parse(happy_response, mode="strict")
    assert cv.mode == "strict"
    assert cv.verdict in {"ACCEPT", "REVISE", "REJECT"}


# ---------- 边界：confidence / verdict mismatch ----------

def test_parse_rejects_confidence_out_of_range(happy_response):
    bad = happy_response.replace('"confidence": 0.72', '"confidence": 1.42')
    with pytest.raises(ConsensusValidationError) as excinfo:
        parse(bad, mode="council")
    assert any("confidence.out_of_range" in v for v in excinfo.value.violations)


def test_parse_rejects_text_arbiter_verdict_vs_summary_json_mismatch(happy_response):
    # summary_json says REVISE, but rewrite arbiter text to say ACCEPT — mismatch.
    bad = happy_response.replace(
        "REVISE — 调整周二", "ACCEPT — 通过原计划"
    )
    with pytest.raises(ConsensusValidationError) as excinfo:
        parse(bad, mode="council")
    assert any("verdict.mismatch" in v for v in excinfo.value.violations)
