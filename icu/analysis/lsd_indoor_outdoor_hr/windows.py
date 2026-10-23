"""稳态持续窗口提取（经过时间轴上），三档严格度。

窗口要求整段都在行进（无静止/缺采），滑行比例、30s 功率变异、前导段稳定性受限。
阈值为**分析筛选参数**，不是生理阀门；三档用于敏感性分析。
"""
from __future__ import annotations

import numpy as np

from io_streams import Ride
from segments import COAST, PEDAL, STILL_GAP, STILL_REC, hr_valid_mask, timeline

LEVELS = {
    "loose":  {"L": 300, "coast_max": 0.15, "cv30_max": 0.25, "lead_s": 0,   "lead_tol": None},
    "medium": {"L": 300, "coast_max": 0.08, "cv30_max": 0.15, "lead_s": 120, "lead_tol": 0.20},
    "strict": {"L": 600, "coast_max": 0.05, "cv30_max": 0.10, "lead_s": 180, "lead_tol": 0.10},
}
MIN_WINDOW_W = 130          # 只收集均功率 ≥ 此值的窗口（排除返程/滑行主导段）
HR_SETTLE_S = 60            # 窗口 HR 取第 60 s 起的均值，减轻进入窗口时的心率延迟
HR_VALID_FRAC = 0.95
STEP_S = 15


def _on_timeline(r: Ride, x: np.ndarray, n: int) -> np.ndarray:
    arr = np.full(n, np.nan)
    arr[r.t] = x
    return arr


def _rolling_mean(x: np.ndarray, w: int) -> np.ndarray:
    """nan 感知滚动均值（右对齐），窗口内有 nan 则结果 nan。"""
    out = np.full_like(x, np.nan)
    good = np.isfinite(x)
    cs = np.concatenate([[0.0], np.cumsum(np.where(good, x, 0.0))])
    cn = np.concatenate([[0], np.cumsum(good)])
    s = cs[w:] - cs[:-w]
    c = cn[w:] - cn[:-w]
    out[w - 1:] = np.where(c == w, s / w, np.nan)
    return out


def ride_arrays(r: Ride) -> dict:
    tl = timeline(r)
    n = len(tl)
    hr = r.hr.copy()
    hr[~hr_valid_mask(r)] = np.nan
    p = _on_timeline(r, r.p, n)
    moving = (tl == PEDAL) | (tl == COAST)
    return {"tl": tl, "p": p, "p30": _rolling_mean(p, 30), "hr": _on_timeline(r, hr, n),
            "cad": _on_timeline(r, r.cad, n), "temp": _on_timeline(r, r.temp, n),
            "moving": moving, "moving_clock": np.concatenate([[0], np.cumsum(moving)[:-1]]),  # 窗口起点之前的行进秒数
            "still": (tl == STILL_REC) | (tl == STILL_GAP)}


def _window_ok(A: dict, a: int, cfg: dict) -> dict | None:
    L = cfg["L"]
    b = a + L
    if not A["moving"][a:b].all():
        return None
    coast = float(np.mean(A["tl"][a:b] == COAST))
    if coast > cfg["coast_max"]:
        return None
    p, p30 = A["p"][a:b], A["p30"][a + 29:b]
    if np.isnan(p).any() or np.isnan(p30).any():
        return None
    pm = float(np.mean(p))
    if pm < MIN_WINDOW_W:
        return None
    cv = float(np.std(p30) / np.mean(p30))
    if cv > cfg["cv30_max"]:
        return None
    hr = A["hr"][a:b]
    if np.mean(np.isfinite(hr)) < HR_VALID_FRAC:
        return None
    if cfg["lead_s"]:
        la = a - cfg["lead_s"]
        if la < 0 or not A["moving"][la:a].all():
            return None
        lp = np.nanmean(A["p"][la:a])
        if abs(lp - pm) / pm > cfg["lead_tol"]:
            return None
    return {"coast_frac": round(coast, 3), "cv30": round(cv, 3), "P": round(pm, 1)}


def _prior_context(A: dict, a: int, look: int = 300) -> dict:
    la = max(0, a - look)
    still = A["still"][la:a]
    p30 = A["p30"][la:a]
    stops = np.where(A["still"][:a])[0]
    return {"prior5min_still_s": int(still.sum()),
            "prior5min_max_p30_W": round(float(np.nanmax(p30)), 1) if np.isfinite(p30).any() else None,
            "s_since_last_still": int(a - stops[-1]) if len(stops) else None}


def steady_windows(r: Ride, level: str) -> list[dict]:
    cfg = LEVELS[level]
    A = ride_arrays(r)
    n, L = len(A["tl"]), cfg["L"]
    out, a = [], 0
    while a + L <= n:
        ok = _window_ok(A, a, cfg)
        if ok is None:
            a += STEP_S
            continue
        b = a + L
        hr_set = A["hr"][a + HR_SETTLE_S:b]
        temp = A["temp"][a:b]
        out.append({
            "start_elapsed_s": int(a), "end_elapsed_s": int(b),
            "start_moving_s": int(A["moving_clock"][a]),
            **ok,
            "cad": round(float(np.nanmean(A["cad"][a:b])), 1),
            "HR_settled": round(float(np.nanmean(hr_set)), 1),
            "HR_first60": round(float(np.nanmean(A["hr"][a:a + HR_SETTLE_S])), 1),
            "temp_device": round(float(np.nanmean(temp)), 2) if np.isfinite(temp).any() else None,
            **_prior_context(A, a),
        })
        a = b
    return out


def hr_power_lag(r: Ride, max_lag: int = 120, min_run: int = 900) -> dict:
    """连续行进段内，去趋势的瞬时功率与 HR 的互相关峰值滞后（秒）。仅描述性。

    用瞬时功率（非 30s 右对齐均值，否则滞后被系统性低估约 14.5s）；
    去趋势用 300s 尾随均值，并丢掉前 299 个样本（不做边缘填充，避免热身爬升主导相关）。
    """
    A = ride_arrays(r)
    best = []
    from segments import continuous_runs
    for a, b in continuous_runs(A["tl"]):
        if b - a < min_run:
            continue
        p = A["p"][a:b]
        h = A["hr"][a:b]
        if np.isnan(p).any() or np.mean(np.isfinite(h)) < 0.98:
            continue
        h = np.where(np.isfinite(h), h, np.nanmean(h))
        pd = (p - _rolling_mean(p, 300))[299:]
        hd = (h - _rolling_mean(h, 300))[299:]
        cors = [np.corrcoef(pd[:len(pd) - k], hd[k:])[0, 1] for k in range(max_lag + 1)]
        k = int(np.nanargmax(cors))
        best.append({"run_start_s": int(a), "run_len_s": int(b - a), "lag_s": k, "r": round(float(cors[k]), 3)})
    lags = [x["lag_s"] for x in best]
    return {"n_runs": len(best), "median_lag_s": float(np.median(lags)) if lags else None, "runs": best}
