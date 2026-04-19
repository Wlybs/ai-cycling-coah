from datetime import date

from src.coach.periodization.ctl_slope import CTLSlope
from src.coach.periodization.race_calendar import RaceEntry
from src.coach.periodization.phase_detector import detect_phase
from src.coach.periodization.types import Phase


def _slope(s: float, interp: str, last_ctl: float = 95.0) -> CTLSlope:
    return CTLSlope(slope_per_day=s, interpretation=interp,
                    sample_size=28, last_ctl=last_ctl)


def test_taper_when_race_within_10_days():
    races = [RaceEntry(name="A", race_date=date(2026, 4, 24),
                       priority="A", days_out=6)]
    phase, reasons = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.1, "flat"),
        races=races,
        ctl_90d_peak=96.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.TAPER
    assert any("6 天" in r or "days_out" in r for r in reasons)


def test_race_day():
    races = [RaceEntry(name="A", race_date=date(2026, 4, 18),
                       priority="A", days_out=0)]
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.0, "flat"),
        races=races,
        ctl_90d_peak=96.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.RACE


def test_peak_when_race_11_to_21_days_and_ctl_near_peak():
    races = [RaceEntry(name="A", race_date=date(2026, 5, 7),
                       priority="A", days_out=19)]
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.0, "flat", last_ctl=95.5),
        races=races,
        ctl_90d_peak=96.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.PEAK


def test_build_when_ctl_increasing_and_quality_on_target():
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.4, "increasing", last_ctl=92.0),
        races=[],
        ctl_90d_peak=92.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.BUILD


def test_base_when_under_prescription_signal():
    phase, reasons = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.05, "flat"),
        races=[],
        ctl_90d_peak=95.0,
        recent_stimulus_median=0.30,  # < 0.4 → BASE
    )
    assert phase is Phase.BASE
    assert any("stimulus" in r for r in reasons)


def test_base_protect_when_ctl_below_75():
    """底盘保护：即使 CTL 在加载、stimulus 正常，CTL<75 一律 BASE。"""
    phase, reasons = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.4, "increasing", last_ctl=70.0),
        races=[],
        ctl_90d_peak=72.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.BASE
    assert any("CTL" in r and "75" in r for r in reasons)


def test_base_protect_ignored_if_race_within_taper_window():
    """赛前 Taper 优先级高于 CTL 保护（临赛不会回 BASE）。"""
    races = [RaceEntry(name="A", race_date=date(2026, 4, 24),
                       priority="A", days_out=6)]
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.4, "increasing", last_ctl=70.0),
        races=races,
        ctl_90d_peak=72.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.TAPER


def test_transition_when_ctl_dropping_without_race():
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(-0.5, "decreasing"),
        races=[],
        ctl_90d_peak=95.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.TRANSITION
