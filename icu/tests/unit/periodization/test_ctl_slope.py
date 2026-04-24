from datetime import date, timedelta

from src.coach.periodization.ctl_slope import (
    CTLSlope, analyze_ctl_slope,
)


def _series(start: date, values: list[float]) -> list[dict]:
    return [
        {"id": (start + timedelta(days=i)).isoformat(), "ctl": v}
        for i, v in enumerate(values)
    ]


def test_positive_slope_build_load():
    values = [80 + i * 0.5 for i in range(28)]
    series = _series(date(2026, 3, 22), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert slope.slope_per_day > 0.3
    assert slope.interpretation == "increasing"
    assert slope.sample_size == 28


def test_flat_slope_plateau():
    values = [94.0] * 28
    series = _series(date(2026, 3, 22), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert abs(slope.slope_per_day) < 0.05
    assert slope.interpretation == "flat"


def test_negative_slope_taper():
    values = [100 - i * 0.8 for i in range(28)]
    series = _series(date(2026, 3, 22), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert slope.slope_per_day < -0.3
    assert slope.interpretation == "decreasing"


def test_short_series_fallback_uses_available_days():
    values = [88 + i * 0.4 for i in range(10)]
    series = _series(date(2026, 4, 9), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert slope.sample_size == 10
    assert slope.slope_per_day > 0.2


def test_missing_ctl_skipped():
    series = [
        {"id": "2026-04-01", "ctl": 90.0},
        {"id": "2026-04-02", "ctl": None},
        {"id": "2026-04-03", "ctl": 91.0},
    ]
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 4), window_days=7)
    assert slope.sample_size == 2


def test_empty_series_returns_none_slope():
    slope = analyze_ctl_slope([], reference_date=date(2026, 4, 18), window_days=28)
    assert slope.slope_per_day is None
    assert slope.interpretation == "unknown"
    assert slope.sample_size == 0


def test_duplicate_dates_deduplicated_last_wins():
    """重复日期只保留最后一条，不应让回归被双倍权重拉偏。"""
    series = [
        {"id": "2026-04-01", "ctl": 90.0},
        {"id": "2026-04-01", "ctl": 95.0},  # duplicate date, different CTL
        {"id": "2026-04-02", "ctl": 96.0},
        {"id": "2026-04-03", "ctl": 97.0},
    ]
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 4), window_days=7)
    assert slope.sample_size == 3  # 4 rows → 3 unique dates
    assert slope.last_ctl == 97.0


def test_future_dates_excluded():
    """reference_date 之后的行应被过滤掉。"""
    series = [
        {"id": "2026-04-01", "ctl": 90.0},
        {"id": "2026-04-02", "ctl": 91.0},
        {"id": "2026-04-05", "ctl": 99.0},  # future relative to ref
    ]
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 3), window_days=7)
    assert slope.sample_size == 2
    assert slope.last_ctl == 91.0
