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
