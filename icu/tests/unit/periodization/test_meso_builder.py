import pytest
from datetime import date, timedelta

from src.coach.periodization.meso_builder import (
    select_meso_pattern, MESO_PATTERNS, build_meso_block,
)
from src.coach.periodization.types import Phase, MacroWindow, PhaseIntent


def test_base_phase_uses_polarized():
    p = select_meso_pattern(
        phase=Phase.BASE, knee_flag=None, recent_atl_delta=0.0)
    assert p == "polarized"


def test_build_default_three_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag=None, recent_atl_delta=2.0)
    assert p == "3:1"


def test_build_high_responder_two_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag=None,
        recent_atl_delta=2.0, response_high_responder=True)
    assert p == "2:1"


def test_knee_caution_forces_three_one_over_two_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag="caution",
        recent_atl_delta=2.0, response_high_responder=True)
    assert p == "3:1"


def test_taper_uses_linear():
    p = select_meso_pattern(
        phase=Phase.TAPER, knee_flag=None, recent_atl_delta=-3.0)
    assert p == "linear"


def test_peak_phase_default_three_one():
    p = select_meso_pattern(
        phase=Phase.PEAK, knee_flag=None, recent_atl_delta=0.0)
    assert p == "3:1"


def test_transition_falls_through_to_three_one():
    p = select_meso_pattern(
        phase=Phase.TRANSITION, knee_flag=None, recent_atl_delta=0.0)
    assert p == "3:1"


def _make_macro_window(
    start: date, end: date, phase: Phase = Phase.BUILD
) -> MacroWindow:
    intent = PhaseIntent(
        phase=phase, primary_adaptation="threshold_capacity",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75.0, "mid": 15.0, "high": 10.0},
        rest_days_per_week=1, rationale="test",
    )
    return MacroWindow(phase=phase, start_date=start, end_date=end, intent=intent)


def test_build_meso_block_aligns_to_monday():
    # reference_date = Sat 2026-04-18; its Monday = 2026-04-13
    macro = _make_macro_window(date(2026, 4, 1), date(2026, 5, 28))
    meso = build_meso_block(
        reference_date=date(2026, 4, 18),
        macro=macro, pattern="3:1",
    )
    assert meso.block_start == date(2026, 4, 13)  # Monday
    assert meso.block_end == date(2026, 4, 13) + timedelta(days=27)
    assert meso.weekly_load_multipliers == [1.00, 1.05, 1.10, 0.70]
    assert meso.phase is Phase.BUILD


def test_build_meso_block_truncates_when_macro_window_ends_sooner():
    # Plan originally used a 10-day macro window expecting 1-2 multipliers,
    # but File 01 types.py enforces min_length=3 on weekly_load_multipliers.
    # Use a 21-day macro window (3 full weeks) so truncation from 4-week
    # "3:1" pattern yields exactly 3 multipliers.
    macro = _make_macro_window(date(2026, 4, 13), date(2026, 5, 3))
    meso = build_meso_block(
        reference_date=date(2026, 4, 13),
        macro=macro, pattern="3:1",
    )
    assert meso.block_end == date(2026, 5, 3)
    assert len(meso.weekly_load_multipliers) == 3
    assert meso.weekly_load_multipliers == [1.00, 1.05, 1.10]


def test_build_meso_block_taper_linear_three_weeks():
    macro = _make_macro_window(
        date(2026, 5, 1), date(2026, 5, 21), phase=Phase.TAPER
    )
    meso = build_meso_block(
        reference_date=date(2026, 5, 1), macro=macro, pattern="linear",
    )
    assert len(meso.weekly_load_multipliers) == 3
    assert meso.weekly_load_multipliers == [1.00, 0.70, 0.40]


def test_build_meso_block_rejects_unknown_pattern():
    macro = _make_macro_window(date(2026, 4, 1), date(2026, 5, 28))
    with pytest.raises(KeyError):
        build_meso_block(
            reference_date=date(2026, 4, 18),
            macro=macro, pattern="does-not-exist",
        )


def test_build_meso_block_floors_multipliers_at_three_when_macro_too_short():
    # Macro window only 14 days (2 weeks) — shorter than the 3-week min_length
    # floor enforced by File 01 MesoBlock. The builder should clip block_end
    # to the macro boundary but keep multipliers count at 3 (Pydantic contract).
    macro = _make_macro_window(date(2026, 4, 13), date(2026, 4, 26))
    meso = build_meso_block(
        reference_date=date(2026, 4, 13),
        macro=macro, pattern="3:1",
    )
    assert meso.block_end == date(2026, 4, 26)
    # Floor guarantees exactly 3 multipliers even though macro window is 2 weeks
    assert len(meso.weekly_load_multipliers) == 3
    assert meso.weekly_load_multipliers == [1.00, 1.05, 1.10]


def test_build_meso_block_type_error_on_non_macrowindow():
    with pytest.raises(TypeError):
        build_meso_block(
            reference_date=date(2026, 4, 13),
            macro="not a MacroWindow",  # type: ignore[arg-type]
            pattern="3:1",
        )


def test_all_patterns_defined():
    assert set(MESO_PATTERNS.keys()) == {"3:1", "2:1", "polarized", "linear"}
    for multipliers in MESO_PATTERNS.values():
        assert 3 <= len(multipliers) <= 6
        assert min(multipliers) < 1.0
        assert max(multipliers) >= 1.0
