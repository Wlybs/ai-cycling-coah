"""Unit tests for src.coach.consensus.council_prompt."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.coach.consensus.council_prompt import (
    VerdictRequest,
    build_council_prompt,
    detect_under_dosed_triggers,
)
from src.coach.ledger.types import AthleteStateRef


# ---------- helpers ----------

def _state(**over) -> AthleteStateRef:
    base = dict(ctl=70.0, atl=68.0, tsb=2.0, w_prime=14_500,
                phase="BUILD", week_of_year=17)
    base.update(over)
    return AthleteStateRef(**base)


def _plan(**over) -> dict:
    """Minimal WeeklyPlan-ish payload for prompt assembly tests."""
    base = {
        "week_start": "2026-04-20",
        "week_end": "2026-04-26",
        "focus_theme": "BUILD",
        "weekly_tss_target": 525,
        "days": [
            {"day_of_week": "Mon", "training_type": "Recovery",
             "name": "Easy Z2", "duration_min": 60, "target_tss": 45,
             "power_range_w": "120-160W", "tier": "EASY"},
            {"day_of_week": "Tue", "training_type": "VO2max",
             "name": "5x4min @CP", "duration_min": 75, "target_tss": 90,
             "power_range_w": "260-280W", "tier": "HIGH"},
            {"day_of_week": "Wed", "training_type": "Endurance",
             "name": "Z2 base", "duration_min": 90, "target_tss": 70,
             "power_range_w": "150-180W", "tier": "MID"},
            {"day_of_week": "Thu", "training_type": "Rest",
             "name": "Rest", "duration_min": 0, "target_tss": 0,
             "power_range_w": None, "tier": "REST"},
            {"day_of_week": "Fri", "training_type": "Threshold",
             "name": "2x20min", "duration_min": 80, "target_tss": 110,
             "power_range_w": "240-260W", "tier": "HIGH"},
            {"day_of_week": "Sat", "training_type": "Endurance",
             "name": "Long Z2", "duration_min": 180, "target_tss": 140,
             "power_range_w": "150-180W", "tier": "MID"},
            {"day_of_week": "Sun", "training_type": "Recovery",
             "name": "Easy spin", "duration_min": 60, "target_tss": 40,
             "power_range_w": "120-150W", "tier": "EASY"},
        ],
    }
    base.update(over)
    return base


def _physiology() -> dict:
    return {
        "cp_w": 285,
        "w_prime_j": 14_500,
        "durability_index": 0.74,
        "response_profile": {
            "types": {
                "vo2max": {"tolerance_class": "high"},
                "threshold": {"tolerance_class": "high"},
            }
        },
        "knee_flag": "OK",
    }


def _wellness_trend() -> list[dict]:
    return [
        {"date": "2026-04-19", "hrv": 62, "rhr": 51, "sleep_h": 7.6},
        {"date": "2026-04-20", "hrv": 65, "rhr": 50, "sleep_h": 7.4},
    ]


def _request(**over) -> "VerdictRequest":
    base = dict(
        plan=_plan(),
        athlete_state=_state(),
        physiology=_physiology(),
        wellness_trend=_wellness_trend(),
        periodization_summary={"phase": "BUILD",
                               "weekly_tss_target": 525,
                               "weeks_to_race": 8},
    )
    base.update(over)
    return VerdictRequest(**base)


# ---------- VerdictRequest schema tests ----------

class TestVerdictRequest:

    def test_required_fields_round_trip(self):
        r = _request()
        # Frozen — assignment must raise.
        with pytest.raises(ValidationError):
            r.plan = {}  # type: ignore[misc]

    def test_missing_plan_raises(self):
        with pytest.raises(ValidationError):
            VerdictRequest(  # type: ignore[call-arg]
                athlete_state=_state(),
                physiology=_physiology(),
                wellness_trend=[],
                periodization_summary={},
            )

    def test_missing_athlete_state_raises(self):
        with pytest.raises(ValidationError):
            VerdictRequest(  # type: ignore[call-arg]
                plan=_plan(),
                physiology=_physiology(),
                wellness_trend=[],
                periodization_summary={},
            )

    def test_wellness_trend_default_empty(self):
        # wellness_trend is optional with default_factory=list
        r = VerdictRequest(
            plan=_plan(),
            athlete_state=_state(),
            physiology=_physiology(),
            periodization_summary={},
        )
        assert r.wellness_trend == []


# ---------- build_council_prompt structural tests ----------

class TestBuildCouncilPromptStructure:

    def test_returns_str(self):
        out = build_council_prompt(_request())
        assert isinstance(out, str)
        assert len(out) > 100

    def test_contains_four_sections_in_order(self):
        out = build_council_prompt(_request())
        idx_a = out.find("## Section A")
        idx_b = out.find("## Section B")
        idx_c = out.find("## Section C")
        idx_d = out.find("## Section D")
        assert idx_a >= 0, "Section A header missing"
        assert idx_b > idx_a, "Section B must follow A"
        assert idx_c > idx_b, "Section C must follow B"
        assert idx_d > idx_c, "Section D must follow C"

    def test_section_a_lists_all_four_roles(self):
        out = build_council_prompt(_request())
        for role in ("Planner", "Critic", "Physiologist", "Arbiter"):
            assert role in out, f"role {role!r} missing from Section A"

    def test_section_a_mentions_under_dosed_check(self):
        out = build_council_prompt(_request())
        # Critic mandate must reference UNDER-DOSED 6-item check (label only;
        # actual triggers fire conditionally — see T65.2).
        assert "UNDER-DOSED" in out

    def test_section_b_includes_plan_summary(self):
        out = build_council_prompt(_request())
        assert "weekly_tss_target" in out or "Weekly TSS" in out
        # Each day-of-week label appears at least once in the plan dump.
        for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
            assert d in out, f"day {d!r} missing from Section B plan dump"

    def test_section_b_includes_physiology(self):
        out = build_council_prompt(_request())
        assert "cp_w" in out or "CP" in out
        assert "w_prime" in out or "W'" in out

    def test_section_b_includes_wellness_trend(self):
        out = build_council_prompt(_request())
        assert "hrv" in out.lower() or "HRV" in out

    def test_section_c_empty_when_no_history(self):
        out = build_council_prompt(_request(), history=None)
        # Sentinel string the parser DOES NOT treat as a triplet
        assert "(no historical context)" in out

    def test_section_c_empty_for_empty_list(self):
        out = build_council_prompt(_request(), history=[])
        assert "(no historical context)" in out

    def test_section_d_specifies_summary_json_block(self):
        out = build_council_prompt(_request())
        assert "<summary_json>" in out
        # Schema must reference the three accept tags.
        assert "ACCEPT" in out and "REVISE" in out and "REJECT" in out

    def test_section_d_specifies_role_tag_blocks(self):
        out = build_council_prompt(_request())
        # Output schema reference must show <planner> / <critic> /
        # <physiologist> / <arbiter> tags so the LLM emits parseable bodies.
        for tag in ("<planner>", "<critic>",
                    "<physiologist>", "<arbiter>"):
            assert tag in out, f"output-schema tag {tag!r} missing"


# ---------- detect_under_dosed_triggers stub for T65.1 ----------

class TestDetectUnderDosedStub:
    """detect_under_dosed_triggers exists and returns []. T65.2 fills it."""

    def test_function_exists(self):
        assert callable(detect_under_dosed_triggers)

    def test_returns_list(self):
        out = detect_under_dosed_triggers(_plan(), _state().model_dump())
        assert isinstance(out, list)


# ---------- T65.2: detect_under_dosed_triggers ----------

class TestDetectUnderDosedTriggers:

    # ---- Trigger 1: hard-day quota ----

    def test_t1_fires_when_zero_hard_days_in_BUILD(self):
        plan = _plan()
        for d in plan["days"]:
            d["tier"] = "EASY"  # no hard days
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="BUILD").model_dump())
        assert "under_dosed.hard_day_quota" in triggers

    def test_t1_fires_when_one_hard_day_in_BUILD(self):
        plan = _plan()
        # exactly 1 HIGH-tier day in BUILD = UNDER-DOSED
        hi = [d for d in plan["days"] if d["tier"] == "HIGH"]
        # default _plan() has 2 HIGH days; collapse one to MID.
        hi[0]["tier"] = "MID"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="BUILD").model_dump())
        assert "under_dosed.hard_day_quota" in triggers

    def test_t1_does_not_fire_with_two_hard_days_in_BUILD(self):
        # default _plan() has 2 HIGH days
        triggers = detect_under_dosed_triggers(
            _plan(), _state(phase="BUILD").model_dump())
        assert "under_dosed.hard_day_quota" not in triggers

    def test_t1_skipped_outside_BUILD(self):
        plan = _plan()
        for d in plan["days"]:
            d["tier"] = "EASY"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="RECOVERY").model_dump())
        # T1 only checks BUILD specifically; outside BUILD no fire
        assert "under_dosed.hard_day_quota" not in triggers

    # ---- Trigger 2: hi-intensity work minutes ----

    def test_t2_fires_when_total_hi_work_below_18min(self):
        plan = _plan()
        for d in plan["days"]:
            if d["training_type"] in ("VO2max", "Threshold"):
                d["duration_min"] = 10  # well below 18min floor
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.hi_intensity_work_minutes" in triggers

    def test_t2_does_not_fire_when_total_hi_work_above_18min(self):
        # default _plan() has 75+80=155min hi (uses duration as proxy)
        triggers = detect_under_dosed_triggers(
            _plan(), _state().model_dump())
        assert "under_dosed.hi_intensity_work_minutes" not in triggers

    # ---- Trigger 3: weekly TSS below band ----

    def test_t3_fires_when_tss_below_load_band(self):
        plan = _plan(weekly_tss_target=300)  # CTL=70 -> band lower bound ~5*CTL=350
        triggers = detect_under_dosed_triggers(
            plan, _state(ctl=70.0).model_dump())
        assert "under_dosed.weekly_tss_below_band" in triggers

    def test_t3_does_not_fire_when_tss_in_band(self):
        plan = _plan(weekly_tss_target=525)  # well within band
        triggers = detect_under_dosed_triggers(
            plan, _state(ctl=70.0).model_dump())
        assert "under_dosed.weekly_tss_below_band" not in triggers

    # ---- Trigger 4: PEAK phase race-sim ----

    def test_t4_fires_in_PEAK_with_no_race_sim(self):
        plan = _plan()
        # default plan has no day named "Race-Sim"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="PEAK").model_dump())
        assert "under_dosed.peak_no_race_sim" in triggers

    def test_t4_does_not_fire_in_PEAK_with_race_sim(self):
        plan = _plan()
        plan["days"][5]["name"] = "Race-Sim 90min"
        plan["days"][5]["training_type"] = "RaceSim"
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="PEAK").model_dump())
        assert "under_dosed.peak_no_race_sim" not in triggers

    def test_t4_skipped_outside_PEAK(self):
        # in BUILD, T4 must not fire even with no race-sim
        triggers = detect_under_dosed_triggers(
            _plan(), _state(phase="BUILD").model_dump())
        assert "under_dosed.peak_no_race_sim" not in triggers

    # ---- Trigger 5: stimulus_score 3-week mean ----

    def test_t5_fires_when_3w_mean_below_0_45(self):
        plan = _plan()
        plan["recent_stimulus_scores"] = [0.4, 0.42, 0.38]
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.stimulus_3w_mean" in triggers

    def test_t5_does_not_fire_when_mean_above_threshold(self):
        plan = _plan()
        plan["recent_stimulus_scores"] = [0.55, 0.60, 0.50]
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.stimulus_3w_mean" not in triggers

    def test_t5_emits_insufficient_data_label_when_key_absent(self):
        plan = _plan()
        plan.pop("recent_stimulus_scores", None)
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert any(t.startswith("under_dosed.stimulus_3w_mean")
                   and "insufficient data" in t for t in triggers)

    # ---- Trigger 6: W' negatives 3-week count ----

    def test_t6_fires_when_three_week_negatives_below_two(self):
        plan = _plan()
        plan["recent_w_prime_negatives"] = [0, 1, 1]  # all under 2
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.w_prime_negatives_3w" in triggers

    def test_t6_does_not_fire_with_two_or_more_negatives(self):
        plan = _plan()
        plan["recent_w_prime_negatives"] = [3, 2, 4]
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert "under_dosed.w_prime_negatives_3w" not in triggers

    def test_t6_emits_insufficient_data_label_when_key_absent(self):
        plan = _plan()
        plan.pop("recent_w_prime_negatives", None)
        triggers = detect_under_dosed_triggers(
            plan, _state().model_dump())
        assert any(t.startswith("under_dosed.w_prime_negatives_3w")
                   and "insufficient data" in t for t in triggers)

    # ---- happy path: no triggers ----

    def test_no_triggers_for_well_dosed_plan(self):
        plan = _plan(weekly_tss_target=525)
        plan["recent_stimulus_scores"] = [0.55, 0.60, 0.55]
        plan["recent_w_prime_negatives"] = [3, 2, 3]
        triggers = detect_under_dosed_triggers(
            plan, _state(phase="BUILD").model_dump())
        assert triggers == []

    # ---- prompt wiring: triggers appear in Section A ----

    def test_triggers_render_in_prompt_section_a_when_present(self):
        # request whose plan triggers T1
        plan = _plan()
        for d in plan["days"]:
            d["tier"] = "EASY"
        req = _request(plan=plan)
        out = build_council_prompt(req)
        assert "UNDER-DOSED HYPOTHESIS" in out
        assert "under_dosed.hard_day_quota" in out

    def test_no_under_dosed_section_when_no_triggers(self):
        plan = _plan(weekly_tss_target=525)
        plan["recent_stimulus_scores"] = [0.55, 0.60, 0.55]
        plan["recent_w_prime_negatives"] = [3, 2, 3]
        req = _request(plan=plan)
        out = build_council_prompt(req)
        # When no triggers, the optional sub-section is omitted entirely.
        assert "UNDER-DOSED HYPOTHESIS" not in out


# ---------- T65.3: history triplet rendering ----------

from src.coach.consensus.history_injector import HistoryTriplet, OUTCOME_PENDING


def _triplet(**over) -> HistoryTriplet:
    base = dict(
        plan_entry_id="01HZZZ" + "0" * 20,
        context={"phase": "BUILD", "total_tss": 520,
                 "ctl": 70.0, "week_of_year": 14,
                 "plan_period": "2026-04-06_2026-04-12"},
        verdict="ACCEPT",
        outcome="consensus.ACCEPT@0.82",
    )
    base.update(over)
    return HistoryTriplet(**base)


class TestSectionCRendering:

    def test_renders_each_triplet_as_bullet(self):
        triplets = [_triplet(),
                    _triplet(plan_entry_id="01ZZZB" + "1" * 20,
                             outcome=OUTCOME_PENDING)]
        out = build_council_prompt(_request(), history=triplets)
        # Both plan_entry_ids appear as backticked code spans.
        assert "01HZZZ" in out
        assert "01ZZZB" in out

    def test_outcome_pending_marked_with_hint(self):
        triplets = [_triplet(outcome=OUTCOME_PENDING)]
        out = build_council_prompt(_request(), history=triplets)
        assert OUTCOME_PENDING in out
        # Hint string the prompt builder adds beside outcome_pending.
        assert "awaiting follow-on entry" in out

    def test_section_c_summary_count_matches_input(self):
        triplets = [_triplet(plan_entry_id="01A" + "0" * 23),
                    _triplet(plan_entry_id="01B" + "1" * 23),
                    _triplet(plan_entry_id="01C" + "2" * 23)]
        out = build_council_prompt(_request(), history=triplets)
        # The Section C header line should report the triplet count.
        assert "3 similar context-verdict-outcome triplet(s)" in out

    def test_no_history_renders_empty_sentinel(self):
        out_none = build_council_prompt(_request(), history=None)
        out_empty = build_council_prompt(_request(), history=[])
        for out in (out_none, out_empty):
            assert "(no historical context)" in out
            assert "context-verdict-outcome triplet(s)" not in out

    def test_verdict_field_renders_safely_when_blank(self):
        # File 06 history_injector currently always sets verdict="" (the
        # plan-time verdict isn't emitted by Phase 2). Assert we don't crash
        # and we render `(none)` so the LLM doesn't see an empty backtick.
        triplets = [_triplet(verdict="")]
        out = build_council_prompt(_request(), history=triplets)
        assert "**verdict**: `(none)`" in out
