"""T67.1 RED — strict_prompt skeleton + step 1 (Planner-only)."""
from __future__ import annotations

import pytest

from src.coach.consensus.council_prompt import VerdictRequest
from src.coach.consensus.history_injector import HistoryTriplet
from src.coach.ledger.types import AthleteStateRef


def _make_request() -> VerdictRequest:
    return VerdictRequest(
        plan={"plan_period": "2026-W17", "weekly_tss_target": 380,
              "days": [
                  {"day": "Mon", "training_type": "Endurance",
                   "duration_min": 90, "tier": "MEDIUM"},
                  {"day": "Wed", "training_type": "VO2max",
                   "duration_min": 75, "tier": "HIGH"},
                  {"day": "Sat", "training_type": "Threshold",
                   "duration_min": 90, "tier": "HIGH"}]},
        athlete_state=AthleteStateRef(
            ctl=68.0, atl=72.0, tsb=-4.0,
            w_prime=18000, phase="BUILD", week_of_year=17),
        physiology={"cp_watts": 288, "w_prime_joules": 18000},
        wellness_trend=[{"date": "2026-04-26", "hrv": 72}],
        periodization_summary={"phase": "BUILD"},
    )


def test_strict_step_to_role_constant_locked() -> None:
    from src.coach.consensus.strict_prompt import STRICT_STEP_TO_ROLE
    assert STRICT_STEP_TO_ROLE == {
        1: "planner", 2: "critic",
        3: "physiologist", 4: "arbiter",
    }


def test_build_strict_prompt_is_callable() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert isinstance(out, str) and out.strip()


def test_step1_contains_planner_role_only_in_section_a() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "<planner>" in out
    assert "Critic (`<critic>`)" not in out
    assert "Physiologist (`<physiologist>`)" not in out
    assert "Arbiter (`<arbiter>`)" not in out


def test_step1_section_b_reused_from_council_prompt() -> None:
    """Section B identical to council mode (verbatim re-import)."""
    from src.coach.consensus import council_prompt as cp_mod
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert cp_mod._section_b(_make_request()) in out


def test_step1_section_c_empty_when_no_history() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "(no historical context)" in out


def test_step1_section_c_renders_history_when_provided() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    triplets = [HistoryTriplet(
        plan_entry_id="01HXYZABCD0123456789ABCDEF",
        context={"ctl": 65, "phase": "BUILD"},
        verdict="ACCEPT", outcome="consensus.ACCEPT@0.78")]
    out = build_strict_prompt(step=1, request=_make_request(),
                              history=triplets)
    assert "01HXYZABCD0123456789ABCDEF" in out


def test_step1_section_d_planner_schema_only() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "<planner>" in out and "</planner>" in out
    assert "<summary_json>" not in out
    assert "<arbiter>" not in out
    assert "<critic>" not in out
    assert "<physiologist>" not in out


def test_step1_no_under_dosed_triggers_in_planner() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request())
    assert "UNDER-DOSED" not in out
    assert "under_dosed" not in out


def test_invalid_step_rejected() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    for bad in (0, -1, 5, 99):
        with pytest.raises(ValueError) as exc:
            build_strict_prompt(step=bad, request=_make_request())
        assert "step" in str(exc.value).lower()


def test_step1_rejects_prior_responses() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    with pytest.raises(ValueError):
        build_strict_prompt(step=1, request=_make_request(),
                            prior_responses={"planner": "<planner>x</planner>"})


def test_step1_accepts_empty_prior_responses() -> None:
    from src.coach.consensus.strict_prompt import build_strict_prompt
    out = build_strict_prompt(step=1, request=_make_request(),
                              prior_responses={})
    assert "<planner>" in out
