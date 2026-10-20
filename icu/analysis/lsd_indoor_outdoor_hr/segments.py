"""按秒的状态时间线：行进踩踏 / 行进滑行 / 记录中静止 / 各类 gap，以及停脚、重启、连续段、路线形态。

所有阈值是**分析筛选参数**，不是生理阀门；默认值集中在 PARAMS，JSON 会原样输出。
"""
from __future__ import annotations

import math

import numpy as np

from io_streams import Ride

PARAMS = {
    "moving_speed_mps": 0.5,          # velocity_smooth > 此值 = 行进
    "gap_stationary_mps": 0.5,        # gap 两端距离差/时长 < 此值 = 静止 gap（含自动暂停，不等于红灯）
    "gap_moving_mps": 2.0,            # ≥ 此值 = 行进中缺采
    "coast_tolerance_s": 10,          # 连续段内允许的最长滑行
    "stop_min_s": 5,                  # 计为一次停脚的最短静止
    "restart_min_stop_s": 10,         # 计算重启输出的前置停脚最短时长
    "restart_window_s": 60,
    "hr_valid_range": (40, 215),
    "hr_spike_bpm_per_s": 25,
    "route_grid_m": 150,
    "route_revisit_gap_s": 300,
}

# 时间线状态码
MISSING, PEDAL, COAST, STILL_REC, STILL_GAP, MOVING_GAP, AMBIG_GAP = range(7)
STATE_NAMES = {MISSING: "unclassified", PEDAL: "moving_pedaling", COAST: "moving_zero_power",
               STILL_REC: "stationary_recorded", STILL_GAP: "stationary_gap",
               MOVING_GAP: "moving_gap_dropout", AMBIG_GAP: "ambiguous_gap"}


def hr_valid_mask(r: Ride) -> np.ndarray:
    lo, hi = PARAMS["hr_valid_range"]
    ok = np.isfinite(r.hr) & (r.hr >= lo) & (r.hr <= hi)
    dhr = np.abs(np.diff(r.hr, prepend=r.hr[0]))
    dt = np.diff(r.t, prepend=r.t[0] - 1)
    ok &= ~((dt == 1) & (dhr > PARAMS["hr_spike_bpm_per_s"]))
    return ok


def recorded_moving(r: Ride) -> np.ndarray:
    """记录样本是否在行进。室内无真实速度：功率>0 或踏频>0 视为行进。"""
    pedaling = (np.nan_to_num(r.p) > 0) | (np.nan_to_num(r.cad) > 0)
    if r.indoor:
        return pedaling
    # 速度缺失（GPS 掉线）时退回用功率/踏频判断，避免把掉线中的踩踏算成静止
    return np.where(np.isfinite(r.v), r.v > PARAMS["moving_speed_mps"], pedaling)


def _gap_state(r: Ride, i: int) -> int:
    dt = r.t[i + 1] - r.t[i]
    dd = r.dist[i + 1] - r.dist[i]
    if not np.isfinite(dd):
        return AMBIG_GAP
    spd = dd / dt
    if r.indoor:
        return STILL_GAP if spd < PARAMS["gap_stationary_mps"] else MOVING_GAP
    if spd < PARAMS["gap_stationary_mps"]:
        return STILL_GAP
    if spd >= PARAMS["gap_moving_mps"]:
        return MOVING_GAP
    return AMBIG_GAP


def timeline(r: Ride) -> np.ndarray:
    """长度 = 经过时间+1 的状态数组（墙钟/经过时间轴）。"""
    tl = np.full(int(r.t[-1]) + 1, MISSING, dtype=np.int8)
    mov = recorded_moving(r)
    pw = np.nan_to_num(r.p)
    tl[r.t[mov & (pw > 0)]] = PEDAL
    tl[r.t[mov & (pw <= 0)]] = COAST
    tl[r.t[~mov]] = STILL_REC
    for i in np.where(np.diff(r.t) > 1)[0]:
        tl[r.t[i] + 1:r.t[i + 1]] = _gap_state(r, i)
    return tl


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """mask 中 True 的连续段 [start, end)。"""
    m = np.concatenate([[False], mask, [False]]).astype(int)
    d = np.diff(m)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def stop_episodes(tl: np.ndarray) -> list[dict]:
    still = (tl == STILL_REC) | (tl == STILL_GAP)
    out = []
    for a, b in _runs(still):
        if b - a >= PARAMS["stop_min_s"]:
            seg = tl[a:b]
            out.append({"start_s": int(a), "dur_s": int(b - a),
                        "recorded_s": int(np.sum(seg == STILL_REC)), "gap_s": int(np.sum(seg == STILL_GAP))})
    return out


def continuous_runs(tl: np.ndarray) -> list[tuple[int, int]]:
    """连续行进段：只含踩踏与≤coast_tolerance的滑行；任何静止/缺采/长滑行断开。"""
    mov = (tl == PEDAL) | (tl == COAST)
    runs = []
    for a, b in _runs(mov):
        seg_start = a
        for ca, cb in _runs(tl[a:b] == COAST):
            if cb - ca > PARAMS["coast_tolerance_s"]:
                if a + ca > seg_start:
                    runs.append((seg_start, a + ca))
                seg_start = a + cb
        if b > seg_start:
            runs.append((seg_start, b))
    return runs


def power_on_timeline(r: Ride) -> np.ndarray:
    arr = np.full(int(r.t[-1]) + 1, np.nan)
    arr[r.t] = r.p
    return arr


def restarts(r: Ride, tl: np.ndarray, stops: list[dict], ftp: float) -> dict:
    pw = power_on_timeline(r)
    peaks = []
    for s in stops:
        if s["dur_s"] < PARAMS["restart_min_stop_s"]:
            continue
        a = s["start_s"] + s["dur_s"]
        seg = pw[a:a + PARAMS["restart_window_s"]]
        seg = seg[np.isfinite(seg)]
        if len(seg) >= 5:
            peaks.append(float(np.max(np.convolve(seg, np.ones(5) / 5, mode="valid"))))
    peaks = np.array(peaks)
    return {"n_restarts_after_stop_ge_10s": int(len(peaks)),
            "median_peak5s_W": round(float(np.median(peaks)), 1) if len(peaks) else None,
            "n_peak5s_above_ftp": int(np.sum(peaks > ftp)),
            "n_peak5s_above_1p5ftp": int(np.sum(peaks > 1.5 * ftp))}


def _bucket(values: list[int], edges: list[int]) -> dict:
    out = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = [v for v in values if lo <= v < hi]
        out[f"{lo}-{hi if hi < 10**8 else 'inf'}s"] = {"n": len(sel), "total_s": int(sum(sel))}
    return out


def stop_and_flow_summary(r: Ride, ftp: float) -> dict:
    tl = timeline(r)
    stops = stop_episodes(tl)
    runs = continuous_runs(tl)
    run_len = [int(b - a) for a, b in runs]
    counts = {STATE_NAMES[k]: int(np.sum(tl == k)) for k in STATE_NAMES}
    pw = power_on_timeline(r)
    pedal_p = pw[tl == PEDAL]
    bands = [(1, 120), (120, 165), (165, 185), (185, 205), (205, 225), (225, 10**4)]
    return {
        "elapsed_s": int(r.t[-1]),
        "recorded_samples": int(len(r.t)),
        "missing_seconds": int(r.t[-1] + 1 - len(r.t)),
        "state_seconds": counts,
        "moving_s": counts["moving_pedaling"] + counts["moving_zero_power"],
        "stops": {"n": len(stops), "total_s": int(sum(s["dur_s"] for s in stops)),
                  "by_duration": _bucket([s["dur_s"] for s in stops], [5, 30, 60, 120, 300, 900, 10**9])},
        "restarts": restarts(r, tl, stops, ftp),
        "continuous_runs": {"n": len(runs), "by_length": _bucket(run_len, [0, 60, 300, 600, 1200, 1800, 10**9]),
                            "time_in_runs_ge_600s": int(sum(x for x in run_len if x >= 600)),
                            "time_in_runs_ge_1200s": int(sum(x for x in run_len if x >= 1200)),
                            "longest_s": int(max(run_len)) if run_len else 0},
        "pedaling_seconds_by_instant_power_W": {f"{a}-{b if b < 10**4 else 'max'}": int(np.sum((pedal_p >= a) & (pedal_p < b)))
                                                 for a, b in bands},
    }


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def route_shape(r: Ride) -> dict | None:
    ok = np.isfinite(r.lat) & np.isfinite(r.lon)
    if r.indoor or ok.sum() < 100:
        return None
    lat, lon, t = r.lat[ok], r.lon[ok], r.t[ok]
    g = PARAMS["route_grid_m"]
    ky = np.round(lat * 111320 / g).astype(int)
    kx = np.round(lon * 111320 * math.cos(math.radians(float(np.mean(lat)))) / g).astype(int)
    visits: dict[tuple, list] = {}
    for x, y, tt in zip(kx, ky, t):
        lst = visits.setdefault((x, y), [])
        if not lst or tt - lst[-1][1] > PARAMS["route_revisit_gap_s"]:
            lst.append([tt, tt])
        else:
            lst[-1][1] = tt
    passes = np.array([len(visits[(x, y)]) for x, y in zip(kx, ky)])
    start = (lat[0], lon[0])
    far = max(_haversine_m(start[0], start[1], a, b) for a, b in zip(lat[::30], lon[::30]))
    return {"valid_latlng_pairs": int(ok.sum()), "latlng_null": int((~ok).sum()),
            "lat_range": [round(float(lat.min()), 5), round(float(lat.max()), 5)],
            "lon_range": [round(float(lon.min()), 5), round(float(lon.max()), 5)],
            "bbox_km": [round((lat.max() - lat.min()) * 111.32, 1),
                        round((lon.max() - lon.min()) * 111.32 * math.cos(math.radians(float(np.mean(lat)))), 1)],
            "max_dist_from_start_km": round(far / 1000, 1),
            "frac_samples_in_cells_passed_ge3": round(float(np.mean(passes >= 3)), 3),
            "unique_cells": len(visits)}
