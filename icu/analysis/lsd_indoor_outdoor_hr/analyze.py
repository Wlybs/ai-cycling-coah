"""主入口：读取→逐 ride 汇总→跨 ride 比较→写 JSON。

    python analyze.py   # 输出 icu/analysis/2026-10-20-lsd-indoor-outdoor-hr-review.json
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import compare as C
from inclusion import EXCLUDED, GROUPS, group_of
from io_streams import LIST_FILE, RAW_DIR, load_activity_list, load_ride, load_snapshot, load_wellness
from segments import PARAMS, route_shape, stop_and_flow_summary
from windows import LEVELS, hr_power_lag, steady_windows

OUT_JSON = Path(__file__).resolve().parents[1] / "2026-10-20-lsd-indoor-outdoor-hr-review.json"
EARLY = {"20-60min": (1200, 3600), "20-40min": (1200, 2400)}
SUMMARY_KEYS = ("start_date_local", "type", "trainer", "name", "distance", "moving_time", "elapsed_time",
                "icu_average_watts", "icu_weighted_avg_watts", "average_heartrate", "average_cadence",
                "average_temp", "average_weather_temp", "icu_training_load", "decoupling", "carbs_ingested",
                "icu_rpe", "feel")


def confounders(meta: dict, acts: list[dict], wellness: dict) -> dict:
    d = date.fromisoformat(meta["start_date_local"][:10])
    prev = (d - timedelta(days=1)).isoformat()
    prev_tl = sum(a.get("icu_training_load") or 0 for a in acts if (a.get("start_date_local") or "")[:10] == prev)
    prior = [a for a in acts if (a.get("start_date_local") or "") < meta["start_date_local"] and a.get("type") in ("Ride", "VirtualRide")]
    w_prev, w_day = wellness.get(prev, {}), wellness.get(d.isoformat(), {})
    ctl, atl = w_prev.get("ctl"), w_prev.get("atl")
    return {"start_hour_local": int(meta["start_date_local"][11:13]),
            "prev_day_training_load": prev_tl,
            "prev_ride": prior[-1]["start_date_local"] + " " + (prior[-1].get("name") or "").split("\n")[0][:40] if prior else None,
            "pre_ride_ctl_atl_tsb_from_prev_day_wellness": [round(ctl, 1) if ctl else None, round(atl, 1) if atl else None,
                                                             round(ctl - atl, 1) if ctl and atl else None],
            "same_day_hrv": w_day.get("hrv"), "same_day_rhr": w_day.get("restingHR"), "same_day_sleep_h": round((w_day.get("sleepSecs") or 0) / 3600, 2),
            "device_avg_temp_C": meta.get("average_temp"), "weather_temp": meta.get("average_weather_temp"),
            "carbs_ingested_field": meta.get("carbs_ingested")}


def first_minutes(r, lo_s: int = 600, hi_s: int = 1200) -> dict:
    """经过时间 10–20min 的行进踩踏样本均值（描述'从一开始'，未做稳态筛选，HR 仍在爬升期）。"""
    from segments import recorded_moving
    sel = (r.t >= lo_s) & (r.t < hi_s) & recorded_moving(r) & (np.nan_to_num(r.p) > 0) & np.isfinite(r.hr)
    if sel.sum() < 60:
        return {"n": int(sel.sum())}
    return {"n": int(sel.sum()), "P": round(float(np.mean(r.p[sel])), 1), "HR": round(float(np.mean(r.hr[sel])), 1),
            "cad": round(float(np.nanmean(r.cad[sel])), 1)}


def build_ride(meta: dict, acts: list[dict], wellness: dict, ftp: float) -> dict:
    r = load_ride(meta)
    return {"id": meta["id"], "date": meta["start_date_local"][:10], "group": group_of(meta["id"]),
            "inclusion_reason": GROUPS[group_of(meta["id"])][meta["id"]],
            "summary": {k: meta.get(k) for k in SUMMARY_KEYS}, "elapsed_s": int(r.t[-1]), "notes": r.notes,
            "route": route_shape(r), "flow": stop_and_flow_summary(r, ftp),
            "hr_power_lag": {k: v for k, v in hr_power_lag(r).items() if k != "runs"},
            "confounders": confounders(meta, acts, wellness),
            "elapsed_10_20min_unscreened": first_minutes(r),
            "windows": {lv: steady_windows(r, lv) for lv in LEVELS}}


def early_section(rides: list[dict]) -> dict:
    out = {}
    for lv in LEVELS:
        for ename, (lo, hi) in EARLY.items():
            for cal_cad in (None, 5.0):
                key = f"{lv}|{ename}|cad_caliper={cal_cad}"
                pairs = C.match_early(rides, lv, lo, hi, cal_p=5.0, cal_cad=cal_cad)
                null = C.match_early(rides, lv, lo, hi, cal_p=5.0, cal_cad=cal_cad, indoor_null=True)
                out[key] = {"summary": C.summarize_pairs(pairs + null), "ride_pairs": pairs, "indoor_null_pairs": null}
    return out


def early_temp(rides: list[dict], lo: int = 1200, hi: int = 3600) -> dict:
    """早段（loose）窗口的设备温度均值；室内 Zwift 无温度流。设备温度受日晒/车把位置影响，非气温。"""
    out = {}
    for r in rides:
        t = [w["temp_device"] for w in r["windows"]["loose"] if C.in_window(w, lo, hi) and w["temp_device"] is not None]
        out[r["id"]] = round(float(np.mean(t)), 2) if t else None
    return out


def main() -> None:
    acts = load_activity_list()
    wellness = load_wellness()
    snap = load_snapshot()
    ftp = float(snap["ftp_set"])
    by_id = {a["id"]: a for a in acts}
    ids = [aid for g in GROUPS.values() for aid in g]
    rides = [build_ride(by_id[aid], acts, wellness, ftp) for aid in ids]

    slopes = {lv: C.fixed_effect_slopes(rides, lv) for lv in ("loose", "medium")}
    adj = {f"{lv}|{e}": C.adjusted_early_hr(rides, lv, slopes[lv], *EARLY[e]) for lv in slopes for e in EARLY}
    drift = {r["id"]: {**{lv: C.ride_drift(r, lv) for lv in ("loose", "medium")},
                       "medium_common_span_le2.5h": C.ride_drift(r, "medium", max_start_s=9000)} for r in rides}
    stop_eff = {r["id"]: C.prior_stop_effect(r) for r in rides if r["group"] == "outdoor_island_lsd"}

    result = {
        "generated_for": "2026-10-20 outdoor vs indoor LSD heart-rate review",
        "sources": {"activity_list": str(LIST_FILE), "streams_dir": str(RAW_DIR),
                    "wellness": "icu_data_warehouse/2_Wellness/wellness_history.json",
                    "snapshot": {"file": "coach_memory/athlete_snapshot.json", "updated_at": snap.get("updated_at"), "ftp_set": ftp}},
        "params": {"segments": PARAMS, "window_levels": LEVELS, "early_windows_s": EARLY, "reference_for_adjustment": C.REF,
                   "match_caliper_W": 5.0, "match_caliper_cad_rpm": [None, 5.0]},
        "groups": {g: list(m) for g, m in GROUPS.items()},
        "excluded": EXCLUDED,
        "rides": rides,
        "early_matching": early_section(rides),
        "fixed_effect_slopes": slopes,
        "adjusted_early_hr": adj,
        "drift": drift,
        "early_window_device_temp_C": early_temp(rides),
        "prior_stop_effect_outdoor_lsd": stop_eff,
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)),
                        encoding="utf-8")
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
