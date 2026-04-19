import json
from datetime import date
from pathlib import Path

from src.coach.periodization.types import (
    MicroCycle, DayIntent, IntensityTier, Phase, PhaseIntent,
)
from src.coach.session_designer.assembler import design_week
from src.coach.session_designer.types import WeeklyPlan


def _micro(phase: Phase = Phase.BUILD) -> MicroCycle:
    intent = PhaseIntent(
        phase=phase, primary_adaptation="threshold_capacity",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )
    template = [
        ("Mon", IntensityTier.REST, 0, "rest"),
        ("Tue", IntensityTier.HARD, 95, "VO2max 5x4' @ 110-115% CP"),
        ("Wed", IntensityTier.EASY, 40, "Z2 recovery 45min"),
        ("Thu", IntensityTier.MEDIUM, 75, "sweet-spot 3x12' @ 88-93% CP"),
        ("Fri", IntensityTier.REST, 0, "rest"),
        ("Sat", IntensityTier.HARD, 110, "threshold 2x20' @ 97-102% CP"),
        ("Sun", IntensityTier.MEDIUM, 180, "endurance 2.5h with 2x10' tempo"),
    ]
    days = [DayIntent(day_of_week=dow, tier=t, target_tss=tss,
                      session_hint=hint) for dow, t, tss, hint in template]
    return MicroCycle(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        phase=phase, intent=intent, days=days,
        weekly_tss_target=500,
    )


def _write_phys(tmp_path):
    p = tmp_path / "coach_memory" / "physiology"
    p.mkdir(parents=True)
    (p / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 280, "w_prime_joules": 22000,
        "fit_r_squared": 0.95, "athlete_ftp_set": 288,
    }))
    (p / "durability.json").write_text(json.dumps({
        "decay_rate_pct_per_1000kj": {"60s": 3.0, "300s": 2.0},
        "sample_size_rides": 12,
    }))
    (p / "response_profile.json").write_text(json.dumps({
        "types": {"Threshold": {"tolerance_class": "medium"},
                  "VO2max": {"tolerance_class": "medium"},
                  "Tempo": {"tolerance_class": "high"}},
        "knee_loading": {"flag": None, "standing_climb_minutes_90d": 0},
    }))
    return tmp_path


def test_design_week_returns_weekly_plan_with_7_days(tmp_path):
    _write_phys(tmp_path)
    plan, sessions, violations = design_week(
        micro_cycle=_micro(),
        memory_dir=tmp_path / "coach_memory",
    )
    assert isinstance(plan, WeeklyPlan)
    assert len(plan.days) == 7
    assert plan.weekly_tss_target == 500
    assert plan.days[0].training_type == "Rest"
    assert plan.days[1].training_type == "VO2max"
    assert len(sessions) == 7


def test_designed_sessions_trace_contains_cp_and_template(tmp_path):
    _write_phys(tmp_path)
    _plan, sessions, _ = design_week(
        micro_cycle=_micro(), memory_dir=tmp_path / "coach_memory",
    )
    tue = [s for s in sessions if s.day_of_week == "Tue"][0]
    assert tue.trace["cp_watts"] == 280
    assert tue.trace["template_name"] == "vo2max_short_5x4"


def test_hard_back_to_back_gets_revised_for_medium_tolerance(tmp_path):
    _write_phys(tmp_path)
    micro = _micro()
    days = list(micro.days)
    days[2] = DayIntent(day_of_week="Wed", tier=IntensityTier.HARD,
                        target_tss=85, session_hint="threshold 2x15'")
    micro = micro.model_copy(update={"days": days})

    plan, _sessions, violations = design_week(
        micro_cycle=micro, memory_dir=tmp_path / "coach_memory",
    )
    wed = plan.days[2]
    assert wed.training_type not in ("VO2max", "Threshold")


def test_clean_plan_has_empty_coaching_summary_pending_prose(tmp_path):
    _write_phys(tmp_path)
    plan, _sessions, _ = design_week(
        micro_cycle=_micro(), memory_dir=tmp_path / "coach_memory",
    )
    assert plan.coaching_summary == ""


def test_missing_physiology_still_produces_plan_using_ftp_fallback(tmp_path):
    mem = tmp_path / "coach_memory"
    mem.mkdir()
    plan, _s, _v = design_week(
        micro_cycle=_micro(), memory_dir=mem, fallback_ftp=285,
    )
    assert plan.weekly_tss_target == 500
    assert len(plan.days) == 7
