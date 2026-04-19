"""组合 CTL 斜率 + 赛历 + 最近 stimulus 中位数 → 当前阶段。
决策表详见 02-phase-detector.md 的 Phase decision rules。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from .ctl_slope import CTLSlope
from .race_calendar import RaceEntry, next_race_after
from .types import Phase

TAPER_WINDOW_DAYS = 10
PEAK_MIN_DAYS = 11
PEAK_MAX_DAYS = 21
CTL_NEAR_PEAK_RATIO = 0.95
SLOPE_BUILD_MIN = 0.2
STIMULUS_UNDER = 0.40
CTL_BASE_PROTECT = 75.0  # 底盘保护阈值（用户决策 2026-04-18）


def _next_a_race(races: list[RaceEntry], ref: date) -> Optional[RaceEntry]:
    a_races = [r for r in races if r.priority.upper() == "A"]
    nxt = next_race_after(a_races, ref)
    if nxt is None:
        return next_race_after(races, ref)
    return nxt


def detect_phase(
    reference_date: date,
    ctl_slope: CTLSlope,
    races: list[RaceEntry],
    ctl_90d_peak: Optional[float],
    recent_stimulus_median: Optional[float],
) -> tuple[Phase, list[str]]:
    """返回 (Phase, reasons)。reasons 供 phase_current.json 记录。"""
    reasons: list[str] = []
    nxt = _next_a_race(races, reference_date)
    days_out = nxt.days_out if nxt else None

    # 1. TAPER / RACE
    if days_out is not None:
        if days_out == 0:
            reasons.append(f"race day: {nxt.name}")
            return Phase.RACE, reasons
        if 0 < days_out <= TAPER_WINDOW_DAYS:
            reasons.append(
                f"A-race in {days_out} 天 ({nxt.name}) → TAPER"
            )
            return Phase.TAPER, reasons

    # 2. PEAK — 11–21 天内有 A 赛且 CTL 已在高位
    if (days_out is not None
            and PEAK_MIN_DAYS <= days_out <= PEAK_MAX_DAYS
            and ctl_slope.last_ctl is not None
            and ctl_90d_peak
            and ctl_90d_peak > 0
            and ctl_slope.last_ctl / ctl_90d_peak >= CTL_NEAR_PEAK_RATIO):
        reasons.append(
            f"A-race in {days_out} 天 + CTL at "
            f"{ctl_slope.last_ctl:.1f}/{ctl_90d_peak:.1f} "
            f"(>{int(CTL_NEAR_PEAK_RATIO*100)}% of 90d peak) → PEAK"
        )
        return Phase.PEAK, reasons

    # 2.5. BASE PROTECT — CTL 过低，强制 BASE（但若已被 TAPER/RACE/PEAK 命中则早已 return）
    if (ctl_slope.last_ctl is not None
            and ctl_slope.last_ctl < CTL_BASE_PROTECT):
        reasons.append(
            f"CTL {ctl_slope.last_ctl:.1f} < {CTL_BASE_PROTECT:.0f} "
            f"→ BASE (底盘保护：CTL 偏低，先打有氧底再上强度)"
        )
        return Phase.BASE, reasons

    # 3. TRANSITION — CTL 下降且未来 28 天没有赛
    future_28d = [r for r in races
                  if 0 <= (r.race_date - reference_date).days <= 28]
    if (ctl_slope.interpretation == "decreasing"
            and ctl_slope.slope_per_day is not None
            and ctl_slope.slope_per_day < -0.3
            and not future_28d):
        reasons.append(
            f"CTL slope {ctl_slope.slope_per_day:+.2f}/d, no race within 28d → TRANSITION"
        )
        return Phase.TRANSITION, reasons

    # 4. BASE — under-prescription
    if (recent_stimulus_median is not None
            and recent_stimulus_median < STIMULUS_UNDER):
        reasons.append(
            f"recent stimulus median {recent_stimulus_median:.2f} "
            f"< {STIMULUS_UNDER} → BASE (under-prescribed, need more volume)"
        )
        return Phase.BASE, reasons

    # 5. BUILD — 加载中、质量达标
    if (ctl_slope.slope_per_day is not None
            and ctl_slope.slope_per_day >= SLOPE_BUILD_MIN
            and (recent_stimulus_median is None
                 or recent_stimulus_median >= 0.45)):
        reasons.append(
            f"CTL rising {ctl_slope.slope_per_day:+.2f}/d, quality on target → BUILD"
        )
        return Phase.BUILD, reasons

    # 6. 默认 BUILD（最保守非减量）
    reasons.append("fallback: no strong signal → BUILD (default)")
    return Phase.BUILD, reasons
