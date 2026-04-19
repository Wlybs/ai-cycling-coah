from datetime import date

from src.coach.periodization.micro_cycle import build_micro_cycle
from src.coach.periodization.types import (
    Phase, PhaseIntent, MesoBlock, IntensityTier,
)


def _intent(phase: Phase, tss: int = 500, rest: int = 1) -> PhaseIntent:
    return PhaseIntent(
        phase=phase, primary_adaptation="x",
        weekly_tss_target=tss,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=rest, rationale="test",
    )


def _meso(phase: Phase = Phase.BUILD) -> MesoBlock:
    return MesoBlock(
        pattern="3:1",
        block_start=date(2026, 4, 13), block_end=date(2026, 5, 10),
        weekly_load_multipliers=[1.00, 1.05, 1.10, 0.70],
        phase=phase,
    )


def test_build_week_applies_load_multiplier_to_tss_target():
    intent = _intent(Phase.BUILD, tss=500)
    meso = _meso()
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20),  # week 2 of 4-week block (idx=1)
        meso=meso,
        intent=intent,
        week_idx=1,
    )
    # multiplier 1.05 → target 525
    assert wk.weekly_tss_target == 525
    assert wk.phase is Phase.BUILD


def test_build_week_has_7_days_and_rest_placement():
    intent = _intent(Phase.BUILD, rest=1)
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20),
        meso=_meso(), intent=intent, week_idx=0,
    )
    dow = [d.day_of_week for d in wk.days]
    assert dow == ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    # Build 模板：Mon + Fri 默认 REST（其实 template 指定 Mon=REST Fri=REST）
    rest_days = [d for d in wk.days if d.tier is IntensityTier.REST]
    assert len(rest_days) >= 1


def test_build_week_two_rest_days_when_intent_requires():
    intent = _intent(Phase.TAPER, rest=2)
    meso = _meso(phase=Phase.TAPER).model_copy(
        update={"weekly_load_multipliers": [1.0, 0.7, 0.4]})
    wk = build_micro_cycle(
        week_start=date(2026, 5, 4), meso=meso, intent=intent, week_idx=0,
    )
    rests = [d for d in wk.days if d.tier is IntensityTier.REST]
    assert len(rests) >= 2


def test_build_week_high_intensity_days_spaced():
    intent = _intent(Phase.BUILD)
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20), meso=_meso(), intent=intent, week_idx=0,
    )
    hard_indices = [i for i, d in enumerate(wk.days)
                    if d.tier is IntensityTier.HARD]
    # 相邻 HARD day 之间至少有一个非 HARD 日
    for i in range(len(hard_indices) - 1):
        assert hard_indices[i+1] - hard_indices[i] >= 2


def test_build_week_tss_sum_within_15pct_of_target():
    intent = _intent(Phase.BUILD, tss=500)
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20), meso=_meso(), intent=intent, week_idx=0,
    )
    actual = sum(d.target_tss for d in wk.days)
    diff = abs(actual - wk.weekly_tss_target)
    # delta-correction makes the sum exactly equal; tolerate ±1 for floor/ceil edge cases
    assert diff <= 1


def test_base_phase_uses_z2_dominant_hints():
    intent = _intent(Phase.BASE)
    wk = build_micro_cycle(
        week_start=date(2026, 2, 2), meso=_meso(phase=Phase.BASE),
        intent=intent, week_idx=0,
    )
    # No HARD days in BASE
    assert all(d.tier is not IntensityTier.HARD for d in wk.days)
    hints = " ".join(d.session_hint for d in wk.days).lower()
    assert "z2" in hints or "endurance" in hints or "long" in hints


def test_week_primary_intent_matches_phase():
    intent = _intent(Phase.PEAK)
    meso = _meso(phase=Phase.PEAK)
    wk = build_micro_cycle(
        week_start=date(2026, 5, 4), meso=meso, intent=intent, week_idx=0,
    )
    assert wk.intent.phase is Phase.PEAK


import pytest


@pytest.mark.parametrize("week_idx,expected_mult", [
    (-1, 1.00),   # clamps to idx 0
    (0, 1.00),
    (3, 0.70),    # last entry of [1.00, 1.05, 1.10, 0.70]
    (99, 0.70),   # clamps to last entry
])
def test_build_week_clamps_week_idx_out_of_range(week_idx, expected_mult):
    intent = _intent(Phase.BUILD, tss=500)
    meso = _meso()
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20), meso=meso, intent=intent, week_idx=week_idx,
    )
    assert wk.weekly_tss_target == int(round(500 * expected_mult))
