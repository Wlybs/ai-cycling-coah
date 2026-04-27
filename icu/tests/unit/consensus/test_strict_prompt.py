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


# ============================================================
# T67.2 — steps 2 / 3 / 4
# ============================================================

_PLANNER_BODY = "<planner>\n- Wed: VO2max 75min @ CP=288W\n</planner>\n"
_CRITIC_BODY = (
    "<critic>\n1. tss=380 < 5*ctl=340.\n"
    "2. work=20min < 25min.\n3. no race-sim.\n</critic>\n"
)
_PHYS_BODY = (
    "<physiologist>\nCP=288W, W'=18000J durability=0.92 "
    "response_profile OK; knee_flag=false.\n</physiologist>\n"
)


def _bsp(step: int, **kw):
    from src.coach.consensus.strict_prompt import build_strict_prompt
    return build_strict_prompt(step=step, request=_make_request(), **kw)


def test_step2_requires_planner_prior() -> None:
    with pytest.raises(ValueError) as exc:
        _bsp(2, prior_responses={})
    assert "planner" in str(exc.value).lower()


def test_step2_embeds_planner_response() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "Prior Planner response" in out
    assert "Wed: VO2max 75min" in out


def test_step2_section_a_critic_only() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "Critic (`<critic>`)" in out
    assert "Planner (`<planner>`)" not in out
    assert "Physiologist (`<physiologist>`)" not in out
    assert "Arbiter (`<arbiter>`)" not in out


def test_step2_under_dosed_triggers_present_for_critic() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "UNDER-DOSED HYPOTHESIS" in out


def test_step2_section_d_critic_only_no_summary_json() -> None:
    out = _bsp(2, prior_responses={"planner": _PLANNER_BODY})
    assert "<critic>" in out
    assert "<summary_json>" not in out


def test_step3_requires_planner_and_critic() -> None:
    with pytest.raises(ValueError) as exc:
        _bsp(3, prior_responses={"planner": _PLANNER_BODY})
    assert "critic" in str(exc.value).lower()


def test_step3_embeds_planner_and_critic_priors() -> None:
    out = _bsp(3, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY})
    assert "Prior Planner response" in out
    assert "Prior Critic response" in out
    assert "tss=380" in out


def test_step3_no_under_dosed_triggers() -> None:
    out = _bsp(3, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY})
    assert "UNDER-DOSED HYPOTHESIS" not in out


def test_step4_requires_all_three_priors() -> None:
    with pytest.raises(ValueError) as exc:
        _bsp(4, prior_responses={
            "planner": _PLANNER_BODY, "critic": _CRITIC_BODY})
    assert "physiologist" in str(exc.value).lower()


def test_step4_embeds_all_three_priors() -> None:
    out = _bsp(4, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY,
        "physiologist": _PHYS_BODY})
    assert "Prior Planner response" in out
    assert "Prior Critic response" in out
    assert "Prior Physiologist response" in out


def test_step4_section_d_arbiter_with_summary_json() -> None:
    out = _bsp(4, prior_responses={
        "planner": _PLANNER_BODY, "critic": _CRITIC_BODY,
        "physiologist": _PHYS_BODY})
    assert "<arbiter>" in out
    assert "<summary_json>" in out
    assert "ACCEPT|REVISE|REJECT" in out


def test_step4_rejects_arbiter_in_prior_responses() -> None:
    """Arbiter is the OUTPUT, never a prior input."""
    with pytest.raises(ValueError) as exc:
        _bsp(4, prior_responses={
            "planner": _PLANNER_BODY, "critic": _CRITIC_BODY,
            "physiologist": _PHYS_BODY,
            "arbiter": "<arbiter>oops</arbiter>"})
    assert "arbiter" in str(exc.value).lower()
