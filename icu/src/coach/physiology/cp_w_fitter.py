import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

import numpy as np
from scipy.optimize import curve_fit

from .types import CPWModel

MMP = Sequence[Sequence[float]]
FIT_LOW_S = 120
FIT_HIGH_S = 1200
R2_THRESHOLD = 0.90


def _hyperbolic_3p(t, cp, w_prime, t_k):
    return cp + w_prime / (t - t_k)


def _hyperbolic_2p(t, cp, w_prime):
    return cp + w_prime / t


def _r_squared(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 1.0
    return 1.0 - ss_res / ss_tot


def hash_mmp(mmp: MMP) -> str:
    s = json.dumps([[float(d), float(p)] for d, p in mmp], sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()


def fit_cp_w(mmp: MMP, athlete_ftp: int, window_days: int) -> CPWModel:
    points = np.array([[float(d), float(p)] for d, p in mmp if d > 0])
    fit_mask = (points[:, 0] >= FIT_LOW_S) & (points[:, 0] <= FIT_HIGH_S)
    fit_points = points[fit_mask] if fit_mask.sum() >= 3 else points
    t = fit_points[:, 0]
    p = fit_points[:, 1]

    cp, w_prime, t_k, r2, model_name = _fit_best(t, p)

    return CPWModel(
        generated_at=datetime.now(timezone.utc).isoformat(),
        window_days=window_days,
        cp_watts=int(round(cp)),
        w_prime_joules=int(round(w_prime)),
        t_k_seconds=float(t_k),
        model=model_name,
        fit_r_squared=float(r2),
        data_points_used=[[float(d), float(pw)] for d, pw in points.tolist()],
        athlete_ftp_set=athlete_ftp,
        cp_vs_ftp_delta_w=int(round(cp)) - athlete_ftp,
    )


def _fit_best(t, p):
    try:
        popt, _ = curve_fit(
            _hyperbolic_3p,
            t,
            p,
            p0=[250.0, 20000.0, -10.0],
            bounds=([100.0, 5000.0, -20.0], [500.0, 50000.0, -5.0]),
            maxfev=10000,
        )
        cp, w_prime, t_k = popt
        r2 = _r_squared(p, _hyperbolic_3p(t, *popt))
        if r2 >= R2_THRESHOLD:
            return cp, w_prime, t_k, r2, "3-param-hyperbolic"
    except Exception:
        pass

    popt, _ = curve_fit(
        _hyperbolic_2p,
        t,
        p,
        p0=[250.0, 20000.0],
        bounds=([100.0, 5000.0], [500.0, 50000.0]),
        maxfev=10000,
    )
    cp, w_prime = popt
    r2 = _r_squared(p, _hyperbolic_2p(t, *popt))
    return cp, w_prime, 0.0, r2, "2-param-hyperbolic"


def write_snapshot(model: CPWModel, base_dir: Path, now_iso: str) -> dict:
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "cp_w_current.json").write_text(model.model_dump_json(indent=2))
    history_dir = base_dir / "history"
    history_dir.mkdir(exist_ok=True)
    year_month = now_iso[:7]
    history_file = history_dir / f"cp_w_{year_month}.json"
    if not history_file.exists():
        history_file.write_text(model.model_dump_json(indent=2))
    return {"current": str(base_dir / "cp_w_current.json"), "history": str(history_file)}


def load_mmp_from_warehouse(warehouse_dir: Path) -> MMP:
    """Read power_curves_90d.json and power_curves_all_time.json; merge peaks per duration."""
    candidates: dict[int, float] = {}
    for name in ("power_curves_90d.json", "power_curves_all_time.json"):
        path = warehouse_dir / "3_PowerData" / name
        if not path.exists():
            continue
        doc = json.loads(path.read_text())
        for d, p in _iter_curve_points(doc):
            if d > 0 and (d not in candidates or p > candidates[d]):
                candidates[d] = p
    return sorted([[d, p] for d, p in candidates.items()])


def _iter_curve_points(doc):
    """Best-effort extraction tolerant to multiple shapes.

    Handles:
      1) Real ICU shape: {"list": [{"after_kj": int, "secs": [..], "watts": [..]}, ...]}
         Only entries with after_kj == 0 (fresh MMP) are yielded.
      2) Legacy synthetic: {"secs": [..], "watts": [..]}
      3) Legacy list-of-dicts: [{"secs": int, "watts": int}, ...]
    """
    # Shape 1: ICU real — {"list": [...]}
    if isinstance(doc, dict) and isinstance(doc.get("list"), list):
        for entry in doc["list"]:
            if not isinstance(entry, dict):
                continue
            if entry.get("after_kj") != 0:
                continue
            secs = entry.get("secs") or []
            watts = entry.get("watts") or []
            for s, w in zip(secs, watts):
                yield s, w
        return
    # Shape 2: dict with parallel arrays
    if isinstance(doc, dict) and "secs" in doc and "watts" in doc:
        yield from zip(doc["secs"], doc["watts"])
        return
    # Shape 3: list of dicts
    if isinstance(doc, list):
        for item in doc:
            if isinstance(item, dict) and "secs" in item and "watts" in item:
                yield item["secs"], item["watts"]
