import pytest
from pydantic import ValidationError

from src.coach.session_designer.types import (
    SessionIntent, WorkoutStep, SessionStructure, DesignedSession,
    WeeklyPlan, DayPlanV2,
)
from src.coach.periodization.types import (
    IntensityTier, SessionType,
)


def test_workout_step_power_range_ordering():
    step = WorkoutStep(
        label="threshold 20min",
        duration_s=1200,
        target_w_low=275, target_w_high=290,
        zone="Z4",
    )
    assert step.duration_s == 1200
    with pytest.raises(ValidationError):
        WorkoutStep(
            label="invalid", duration_s=600,
            target_w_low=300, target_w_high=280, zone="Z4",
        )


def test_workout_step_rpm_range_ordering():
    WorkoutStep(
        label="cadence block", duration_s=600,
        target_rpm_low=85, target_rpm_high=95, zone="Z2",
    )
    with pytest.raises(ValidationError):
        WorkoutStep(
            label="bad cadence", duration_s=600,
            target_rpm_low=100, target_rpm_high=80, zone="Z2",
        )


def test_session_structure_total_duration():
    s = SessionStructure(steps=[
        WorkoutStep(label="WU", duration_s=900,
                    target_w_low=120, target_w_high=200, zone="Z1"),
        WorkoutStep(label="main", duration_s=1800,
                    target_w_low=275, target_w_high=290, zone="Z4"),
        WorkoutStep(label="CD", duration_s=600,
                    target_w_low=100, target_w_high=180, zone="Z1"),
    ])
    assert s.total_duration_s == 3300
    assert s.main_duration_s == 1800


def test_session_intent_minimal():
    si = SessionIntent(
        day_of_week="Tue",
        tier=IntensityTier.HARD,
        target_tss=95,
        session_hint="VO2max 5x4' @ 110-115% CP",
    )
    assert si.tier is IntensityTier.HARD


def test_designed_session_requires_matching_duration():
    s = SessionStructure(steps=[
        WorkoutStep(label="WU", duration_s=900,
                    target_w_low=120, target_w_high=200, zone="Z1"),
        WorkoutStep(label="main", duration_s=1200,
                    target_w_low=275, target_w_high=290, zone="Z4"),
    ])
    ds = DesignedSession(
        day_of_week="Tue", date="2026-04-21",
        session_type=SessionType.THRESHOLD, name="Threshold 20min",
        description="warmup, 1x20' @ 95-100% CP, cooldown",
        duration_min=35, target_tss=75, structure=s,
        power_range_w="275-290W",
    )
    assert ds.session_type is SessionType.THRESHOLD
    # duration_min 必须与 structure 合并后的 total_duration 在 ±5% 范围
    assert abs(ds.duration_min * 60 - s.total_duration_s) <= s.total_duration_s * 0.05


def test_weekly_plan_backwards_compat_with_day_plan_fields():
    """WeeklyPlan 必须和旧 plan_generator.DayPlan 字段完全兼容（ICU 日历同步依赖）。"""
    day = DayPlanV2(
        date="2026-04-21", day_of_week="Tue",
        training_type="Threshold", icu_type="Ride",
        name="Threshold 2x20",
        description="warmup 15min; 2x20' @ 95-100% CP r8'; cd 10min",
        duration_min=85, target_tss=95,
        power_range_w="275-290W", hr_range_bpm=None,
    )
    plan = WeeklyPlan(
        week_start="2026-04-20", week_end="2026-04-26",
        focus_theme="threshold + VO2max",
        weekly_tss_target=525,
        coaching_summary="build week 2 of 4; ramp +1.05x",
        days=[day],
    )
    # 关键字段必须全部 dumpable 成与旧结构一致的 JSON
    js = plan.model_dump()
    assert js["days"][0]["training_type"] == "Threshold"
    assert js["days"][0]["icu_type"] == "Ride"
