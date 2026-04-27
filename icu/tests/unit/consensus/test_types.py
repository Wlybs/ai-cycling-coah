"""Unit tests for consensus types: ExpertTurn, CouncilVerdict, exceptions."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.coach.consensus.types import (
    EXPERT_ROLES,
    VERDICTS,
    MODES,
    ConsensusValidationError,
    CouncilVerdict,
    ExpertTurn,
)


# ---------- ExpertTurn ----------

def test_expert_turn_roundtrip():
    turn = ExpertTurn(
        role="critic",
        body_md="**Point 1.** TSS 偏低，仅 320 vs target 480 ...",
        cited_data=["weekly_plan.total_tss=320", "phase=BUILD"],
    )
    js = turn.model_dump_json()
    loaded = ExpertTurn.model_validate_json(js)
    assert loaded == turn


def test_expert_turn_rejects_unknown_role():
    with pytest.raises(ValidationError):
        ExpertTurn(role="coach", body_md="...", cited_data=[])


def test_expert_turn_role_enum_matches_blueprint():
    # 00-index.md locks these 4; adding a 5th requires an ADR.
    assert set(EXPERT_ROLES) == {"planner", "critic", "physiologist", "arbiter"}


def test_expert_turn_body_md_must_not_be_blank():
    with pytest.raises(ValidationError):
        ExpertTurn(role="planner", body_md="   \n\t ", cited_data=[])


# ---------- CouncilVerdict ----------

def _make_turns() -> list[ExpertTurn]:
    return [
        ExpertTurn(role="planner",  body_md="P body", cited_data=["a", "b"]),
        ExpertTurn(role="critic",   body_md="C body",
                   cited_data=["x1", "x2", "x3"]),
        ExpertTurn(role="physiologist", body_md="Phys body",
                   cited_data=["CP=288", "W'=18500", "durability"]),
        ExpertTurn(role="arbiter",  body_md="A body", cited_data=[]),
    ]


def test_council_verdict_roundtrip_all_three_verdicts():
    for v in VERDICTS:
        cv = CouncilVerdict(
            mode="council",
            verdict=v,
            confidence=0.7,
            justification="一句话理由。",
            expert_turns=_make_turns(),
            summary_json={"verdict": v, "confidence": 0.7,
                          "critic_hard_points": ["a", "b", "c"]},
        )
        js = cv.model_dump_json()
        loaded = CouncilVerdict.model_validate_json(js)
        assert loaded == cv
        assert loaded.verdict == v


def test_council_verdict_rejects_unknown_verdict():
    with pytest.raises(ValidationError):
        CouncilVerdict(
            mode="council", verdict="MAYBE", confidence=0.5,
            justification="x", expert_turns=_make_turns(), summary_json={},
        )


def test_council_verdict_confidence_range():
    base = dict(
        mode="council", verdict="ACCEPT", justification="x",
        expert_turns=_make_turns(), summary_json={},
    )
    CouncilVerdict(**base, confidence=0.0)
    CouncilVerdict(**base, confidence=1.0)
    with pytest.raises(ValidationError):
        CouncilVerdict(**base, confidence=-0.01)
    with pytest.raises(ValidationError):
        CouncilVerdict(**base, confidence=1.01)


def test_council_verdict_mode_enum():
    assert set(MODES) == {"council", "strict"}
    with pytest.raises(ValidationError):
        CouncilVerdict(
            mode="ad-hoc", verdict="ACCEPT", confidence=0.7,
            justification="x", expert_turns=_make_turns(), summary_json={},
        )


def test_council_verdict_requires_four_distinct_roles():
    """council mode 必须包含 planner/critic/physiologist/arbiter 各一条。"""
    only_three = _make_turns()[:3]
    with pytest.raises(ValidationError):
        CouncilVerdict(
            mode="council", verdict="ACCEPT", confidence=0.7,
            justification="x", expert_turns=only_three, summary_json={},
        )


def test_council_verdict_strict_mode_bypasses_four_role_requirement():
    """strict 模式 (4 份独立 response 拼接) 不要求 4 个 role 都齐 — 调用方负责拼装。"""
    cv = CouncilVerdict(
        mode="strict",
        verdict="ACCEPT",
        confidence=0.9,
        justification="strict-mode single arbiter run",
        expert_turns=[ExpertTurn(role="arbiter", body_md="ok", cited_data=[])],
        summary_json={"verdict": "ACCEPT", "confidence": 0.9},
    )
    assert cv.mode == "strict"
    assert len(cv.expert_turns) == 1
    assert cv.expert_turns[0].role == "arbiter"


def test_council_verdict_revise_requires_changes():
    """REVISE 必须在 summary_json 内带 changes 列表，否则违反语义。"""
    cv = CouncilVerdict(
        mode="council", verdict="REVISE", confidence=0.6,
        justification="把周三换成 endurance",
        expert_turns=_make_turns(),
        summary_json={
            "verdict": "REVISE",
            "confidence": 0.6,
            "critic_hard_points": ["a", "b", "c"],
            "changes": [{"day": "Wed", "from": "VO2max", "to": "Endurance"}],
        },
    )
    assert cv.summary_json["changes"][0]["day"] == "Wed"


# ---------- Exception ----------

def test_consensus_validation_error_carries_violations():
    err = ConsensusValidationError(
        violations=["critic.points<3", "physiologist.keywords<3"],
    )
    assert "critic.points<3" in str(err)
    assert err.violations == [
        "critic.points<3", "physiologist.keywords<3",
    ]


def test_consensus_validation_error_requires_nonempty():
    with pytest.raises(ValueError):
        ConsensusValidationError(violations=[])
