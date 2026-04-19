"""CTL 斜率分析。用 N 天线性回归估计 CTL/d，用于识别加载/平台/减量阶段。"""
from __future__ import annotations

import warnings
from datetime import date, datetime
from typing import Literal, Optional

import numpy as np
from pydantic import BaseModel


class CTLSlope(BaseModel):
    slope_per_day: Optional[float]
    interpretation: Literal["increasing", "flat", "decreasing", "unknown"]
    sample_size: int
    window_start: Optional[date] = None
    window_end: Optional[date] = None
    last_ctl: Optional[float] = None


def _parse_date(v: str) -> Optional[date]:
    try:
        return datetime.strptime(v[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


FLAT_THRESHOLD_PER_DAY = 0.1  # |slope| < 0.1 CTL/d 视为持平


def analyze_ctl_slope(
    wellness_history: list[dict],
    reference_date: date,
    window_days: int = 28,
) -> CTLSlope:
    """从 wellness 列表中按 reference_date 回溯 window_days 做线性拟合。"""
    if not wellness_history:
        return CTLSlope(slope_per_day=None, interpretation="unknown", sample_size=0)

    pairs: list[tuple[date, float]] = []
    for row in wellness_history:
        d = _parse_date(row.get("id", ""))
        ctl = row.get("ctl")
        if d is None or ctl is None:
            continue
        age = (reference_date - d).days
        if 0 <= age < window_days:
            pairs.append((d, float(ctl)))
    if not pairs:
        return CTLSlope(slope_per_day=None, interpretation="unknown", sample_size=0)

    # Dedup: if multiple rows share the same date, keep the last one
    pairs = list({d: (d, v) for d, v in pairs}.values())
    pairs.sort(key=lambda p: p[0])
    xs = np.array([(p[0] - pairs[0][0]).days for p in pairs], dtype=float)
    ys = np.array([p[1] for p in pairs], dtype=float)
    if len(pairs) < 2:
        return CTLSlope(
            slope_per_day=0.0, interpretation="flat", sample_size=1,
            window_start=pairs[0][0], window_end=pairs[0][0],
            last_ctl=pairs[0][1],
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", np.RankWarning)
        slope, _ = np.polyfit(xs, ys, 1)
    if slope > FLAT_THRESHOLD_PER_DAY:
        interp = "increasing"
    elif slope < -FLAT_THRESHOLD_PER_DAY:
        interp = "decreasing"
    else:
        interp = "flat"
    return CTLSlope(
        slope_per_day=float(slope),
        interpretation=interp,
        sample_size=len(pairs),
        window_start=pairs[0][0],
        window_end=pairs[-1][0],
        last_ctl=pairs[-1][1],
    )
