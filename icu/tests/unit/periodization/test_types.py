from src.coach.periodization.types import Phase, IntensityTier, SessionType

def test_phase_enum_values():
    expected = {"BASE", "BUILD", "PEAK", "TAPER", "RACE", "TRANSITION"}
    assert {p.value for p in Phase} == expected

def test_intensity_tier_ordering():
    tiers = [IntensityTier.REST, IntensityTier.EASY, IntensityTier.MEDIUM,
             IntensityTier.HARD, IntensityTier.RACE_SIM]
    # 约定：order 由 ordinal 属性保证
    ordinals = [t.ordinal for t in tiers]
    assert ordinals == sorted(ordinals)

def test_session_type_matches_legacy_training_type():
    # 必须与 plan_generator.DayPlan.training_type Literal 一致，ICU 日历同步依赖
    expected = {"Rest", "Recovery", "Aerobic", "Tempo",
                "Threshold", "VO2max", "Neuromuscular", "Race"}
    assert {s.value for s in SessionType} == expected


from datetime import date
import pytest
from pydantic import ValidationError

from src.coach.periodization.types import (
    PhaseIntent, MacroPlan, MacroWindow, MesoBlock, MicroCycle, DayIntent,
    PeriodizationSnapshot, Phase, IntensityTier,
)


def test_phase_intent_required_fields():
    intent = PhaseIntent(
        phase=Phase.BUILD,
        primary_adaptation="threshold_capacity",
        weekly_tss_target=550,
        intensity_distribution_pct={"low": 70, "mid": 20, "high": 10},
        rest_days_per_week=1,
        rationale="Base done; CTL 94 stable; build 4-week block.",
    )
    assert intent.phase is Phase.BUILD
    assert sum(intent.intensity_distribution_pct.values()) == 100


def test_phase_intent_invalid_distribution_rejected():
    with pytest.raises(ValidationError):
        PhaseIntent(
            phase=Phase.BASE,
            primary_adaptation="aerobic_base",
            weekly_tss_target=450,
            intensity_distribution_pct={"low": 60, "mid": 20, "high": 10},  # sum=90
            rest_days_per_week=1,
            rationale="x",
        )


def test_macro_window_has_dates_and_intent():
    w = MacroWindow(
        phase=Phase.TAPER,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 10),
        intent=PhaseIntent(
            phase=Phase.TAPER,
            primary_adaptation="freshness_preservation",
            weekly_tss_target=300,
            intensity_distribution_pct={"low": 60, "mid": 10, "high": 30},
            rest_days_per_week=2,
            rationale="Mujika 2009 taper: vol -50%, intensity preserved.",
        ),
    )
    assert (w.end_date - w.start_date).days == 9


def _build_intent_fixture(phase=Phase.BUILD):
    return PhaseIntent(
        phase=phase, primary_adaptation="threshold_capacity",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )


def test_micro_cycle_seven_day_intents_required():
    days = [
        DayIntent(day_of_week="Mon", tier=IntensityTier.REST,
                  target_tss=0, session_hint="complete rest"),
        DayIntent(day_of_week="Tue", tier=IntensityTier.HARD,
                  target_tss=95, session_hint="VO2max"),
        DayIntent(day_of_week="Wed", tier=IntensityTier.EASY,
                  target_tss=40, session_hint="recovery spin"),
        DayIntent(day_of_week="Thu", tier=IntensityTier.MEDIUM,
                  target_tss=75, session_hint="tempo"),
        DayIntent(day_of_week="Fri", tier=IntensityTier.REST,
                  target_tss=0, session_hint="rest"),
        DayIntent(day_of_week="Sat", tier=IntensityTier.HARD,
                  target_tss=110, session_hint="threshold"),
        DayIntent(day_of_week="Sun", tier=IntensityTier.EASY,
                  target_tss=130, session_hint="long Z2"),
    ]
    cycle = MicroCycle(
        week_start=date(2026, 4, 20),
        week_end=date(2026, 4, 26),
        phase=Phase.BUILD,
        intent=_build_intent_fixture(),   # PhaseIntent, not DayIntent
        days=days,
        weekly_tss_target=450,
    )
    assert len(cycle.days) == 7
    assert cycle.weekly_tss_target == 450


def test_micro_cycle_rejects_non_seven_day():
    with pytest.raises(ValidationError):
        MicroCycle(
            week_start=date(2026, 4, 20),
            week_end=date(2026, 4, 26),
            phase=Phase.BUILD,
            intent=_build_intent_fixture(),
            days=[],  # empty
            weekly_tss_target=450,
        )


def test_periodization_snapshot_composition():
    intent = PhaseIntent(
        phase=Phase.BUILD, primary_adaptation="threshold",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="x",
    )
    macro = MacroPlan(
        generated_at="2026-04-18T00:00:00Z",
        season_end_date=date(2026, 9, 30),
        windows=[MacroWindow(
            phase=Phase.BUILD, start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28), intent=intent,
        )],
    )
    meso = MesoBlock(
        pattern="3:1",
        block_start=date(2026, 4, 6), block_end=date(2026, 4, 26),
        weekly_load_multipliers=[1.0, 1.05, 1.1, 0.7],
        phase=Phase.BUILD,
    )
    micro = MicroCycle(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        phase=Phase.BUILD, intent=intent,
        days=[DayIntent(day_of_week=d, tier=IntensityTier.EASY,
                        target_tss=40, session_hint="x")
              for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]],
        weekly_tss_target=450,
    )
    snap = PeriodizationSnapshot(
        generated_at="2026-04-18T00:00:00Z",
        current_phase=Phase.BUILD,
        macro=macro, meso=meso, micro=micro,
        next_race=None,
    )
    js = snap.model_dump_json()
    assert "BUILD" in js
