"""跨 ride 的比较：早段窗口匹配、组内固定效应斜率、调整后早段 HR、同 ride 漂移、停脚前史。

统计单位以 ride 为准；窗口对之间不独立，只用于描述，不给伪精确置信区间。
"""
from __future__ import annotations

import numpy as np

REF = {"P": 180.0, "cad": 85.0, "t_h": 40 / 60}
OUTDOOR = ("outdoor_island_lsd", "outdoor_continuous_loop")


def in_window(w: dict, lo_s: int, hi_s: int) -> bool:
    return w["start_elapsed_s"] >= lo_s and w["end_elapsed_s"] <= hi_s


def match_early(rides: list[dict], level: str, lo_s: int, hi_s: int, cal_p: float, cal_cad: float | None,
                indoor_null: bool = False) -> list[dict]:
    """每个户外 ride × 室内 ride：早段窗口按 |ΔP|≤cal_p（及可选 |Δcad|）配对，报 ride 对的中位 ΔHR。

    indoor_null=True 时改为室内 × 室内（每对只算一次），作为"同环境不同日"的离散度参照。
    """
    out = []
    ins = [r for r in rides if r["group"].startswith("indoor")]
    outs = ins if indoor_null else [r for r in rides if r["group"] in OUTDOOR]
    for k, ro in enumerate(outs):
        wo = [w for w in ro["windows"][level] if in_window(w, lo_s, hi_s)]
        for ri in (ins[k + 1:] if indoor_null else ins):
            wi = [w for w in ri["windows"][level] if in_window(w, lo_s, hi_s)]
            pairs = []
            for a in wo:
                cands = [b for b in wi if abs(a["P"] - b["P"]) <= cal_p
                         and (cal_cad is None or abs(a["cad"] - b["cad"]) <= cal_cad)]
                if cands:
                    b = min(cands, key=lambda x: abs(a["P"] - x["P"]))
                    pairs.append((a["HR_settled"] - b["HR_settled"], a["P"] - b["P"], a["cad"] - b["cad"]))
            if pairs:
                arr = np.array(pairs)
                out.append({"outdoor": ro["id"], "indoor": ri["id"], "outdoor_group": "indoor_null" if indoor_null else ro["group"],
                            "n_outdoor_windows_matched": len(pairs), "n_outdoor_windows_available": len(wo),
                            "median_dHR": round(float(np.median(arr[:, 0])), 1),
                            "mean_dP": round(float(np.mean(arr[:, 1])), 1),
                            "mean_dcad": round(float(np.mean(arr[:, 2])), 1)})
    return out


def summarize_pairs(pairs: list[dict]) -> dict:
    res = {}
    for g in OUTDOOR + ("indoor_null",):
        v = [p["median_dHR"] for p in pairs if p["outdoor_group"] == g]
        if g == "indoor_null":
            v = [abs(x) for x in v]  # 室内两两比较没有方向，报绝对差
        rides = sorted({p["outdoor"] for p in pairs if p["outdoor_group"] == g})
        res[g] = {"n_ride_pairs": len(v), "n_outdoor_rides": len(rides),
                  "median_of_pair_medians": round(float(np.median(v)), 1) if v else None,
                  "min": min(v) if v else None, "max": max(v) if v else None,
                  "n_positive": sum(x > 0 for x in v)}
    return res


def _design(ws: list[dict], indoor: bool) -> np.ndarray:
    t = np.array([w["start_elapsed_s"] / 3600 for w in ws])
    return np.column_stack([[w["P"] for w in ws], [w["cad"] for w in ws], t * indoor, t * (not indoor)])


def fixed_effect_slopes(rides: list[dict], level: str, min_start_s: int = 1200) -> dict:
    """ride 内去均值后的 OLS：HR ~ P + cad + t(室内) + t(户外)。只用 ride 内变异。"""
    X, y = [], []
    for r in rides:
        ws = [w for w in r["windows"][level] if w["start_elapsed_s"] >= min_start_s]
        if len(ws) < 4:
            continue
        x = _design(ws, r["group"].startswith("indoor"))
        h = np.array([w["HR_settled"] for w in ws])
        X.append(x - x.mean(axis=0))
        y.append(h - h.mean())
    X, y = np.vstack(X), np.concatenate(y)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return {"bpm_per_W": round(float(beta[0]), 3), "bpm_per_rpm": round(float(beta[1]), 3),
            "bpm_per_h_indoor": round(float(beta[2]), 2), "bpm_per_h_outdoor": round(float(beta[3]), 2),
            "n_windows": int(len(y)), "resid_sd_bpm": round(float(np.std(resid)), 2),
            "note": "within-ride variation only; power range inside a ride is narrow so bpm_per_W is weakly identified"}


def adjusted_early_hr(rides: list[dict], level: str, slopes: dict, lo_s: int, hi_s: int) -> list[dict]:
    out = []
    for r in rides:
        indoor = r["group"].startswith("indoor")
        bt = slopes["bpm_per_h_indoor" if indoor else "bpm_per_h_outdoor"]
        ws = [w for w in r["windows"][level] if in_window(w, lo_s, hi_s)]
        if not ws:
            out.append({"id": r["id"], "group": r["group"], "n": 0})
            continue
        adj = [w["HR_settled"] - slopes["bpm_per_W"] * (w["P"] - REF["P"]) - slopes["bpm_per_rpm"] * (w["cad"] - REF["cad"])
               - bt * (w["start_elapsed_s"] / 3600 - REF["t_h"]) for w in ws]
        out.append({"id": r["id"], "group": r["group"], "date": r["date"], "n": len(ws),
                    "raw_HR": round(float(np.mean([w["HR_settled"] for w in ws])), 1),
                    "P": round(float(np.mean([w["P"] for w in ws])), 1), "cad": round(float(np.mean([w["cad"] for w in ws])), 1),
                    "adj_HR_at_ref": round(float(np.mean(adj)), 1)})
    return out


def ride_drift(r: dict, level: str, band_halfwidth: float = 12.0, tail_exclude_s: int = 1800,
               max_start_s: int | None = None) -> dict:
    """同 ride：以早段窗口中位功率为参考带，带内窗口 HR 对经过时间回归（含功率项）。排除最后30min。

    max_start_s 限定窗口起点上限，用于在共同时间跨度内比较室内（较短）与户外（较长）。
    """
    ws = [w for w in r["windows"][level] if w["start_elapsed_s"] >= 1200
          and w["end_elapsed_s"] <= r["elapsed_s"] - tail_exclude_s
          and (max_start_s is None or w["start_elapsed_s"] <= max_start_s)]
    early = [w for w in ws if w["end_elapsed_s"] <= 3600]
    if not early or len(ws) < 4:
        return {"usable": False, "reason": "早段或全程合格窗口不足", "n_windows": len(ws)}
    ref_p = float(np.median([w["P"] for w in early]))
    band = [w for w in ws if abs(w["P"] - ref_p) <= band_halfwidth]
    t = np.array([w["start_elapsed_s"] / 3600 for w in band])
    if len(band) < 4 or t.max() - t.min() < 1.0:
        return {"usable": False, "reason": "参考功率带内窗口<4或时间跨度<1h", "ref_P": round(ref_p, 1), "n_band": len(band)}
    h = np.array([w["HR_settled"] for w in band])
    p = np.array([w["P"] for w in band])
    X = np.column_stack([np.ones_like(t), t, p - ref_p])
    beta, *_ = np.linalg.lstsq(X, h, rcond=None)
    first, last = band[0], band[-1]
    return {"usable": True, "ref_P": round(ref_p, 1), "n_band": len(band),
            "t_span_h": [round(float(t.min()), 2), round(float(t.max()), 2)],
            "slope_bpm_per_h": round(float(beta[1]), 2), "intercept_at_t0_refP": round(float(beta[0]), 1),
            "first_band_window": {k: first[k] for k in ("start_elapsed_s", "P", "cad", "HR_settled")},
            "last_band_window": {k: last[k] for k in ("start_elapsed_s", "P", "cad", "HR_settled")},
            "cad_first_last": [first["cad"], last["cad"]]}


def prior_stop_effect(r: dict, level: str = "loose") -> dict | None:
    """同 ride 内：前5min 有停脚 vs 无停脚的窗口，先按 HR~P+t 去趋势再比残差。"""
    ws = [w for w in r["windows"][level] if w["start_elapsed_s"] >= 1200]
    if len(ws) < 6:
        return None
    t = np.array([w["start_elapsed_s"] / 3600 for w in ws])
    p = np.array([w["P"] for w in ws])
    h = np.array([w["HR_settled"] for w in ws])
    X = np.column_stack([np.ones_like(t), t, p])
    beta, *_ = np.linalg.lstsq(X, h, rcond=None)
    res = h - X @ beta
    stopped = np.array([w["prior5min_still_s"] > 0 for w in ws])
    if stopped.sum() < 2 or (~stopped).sum() < 2:
        return {"n_with_stop": int(stopped.sum()), "n_without": int((~stopped).sum()), "diff": None}
    return {"n_with_stop": int(stopped.sum()), "n_without": int((~stopped).sum()),
            "resid_with_minus_without_bpm": round(float(res[stopped].mean() - res[~stopped].mean()), 1)}
