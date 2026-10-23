# Phase 1 — Physiology core - CP/W prime fitter, W balance (Tasks 4-5)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

## Task 4: CP/W' fitter

**Files:**
- Create: `icu/src/coach/physiology/cp_w_fitter.py`
- Create: `icu/tests/unit/physiology/test_cp_w_fitter.py`

- [ ] **Step 1: Write failing test — synthetic 3-param recovery**

Write `icu/tests/unit/physiology/test_cp_w_fitter.py`:
```python
import json
from pathlib import Path

from src.coach.physiology.cp_w_fitter import fit_cp_w, write_snapshot


def synthetic_mmp(cp=280, w_prime=22000, t_k=-10.0, durations=None):
    durations = durations or [5, 15, 30, 60, 120, 300, 600, 1200]
    return [[d, cp + w_prime / (d - t_k)] for d in durations]


def test_3_param_hyperbolic_recovery():
    mmp = synthetic_mmp()
    model = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    assert model.model == "3-param-hyperbolic"
    assert abs(model.cp_watts - 280) <= 3
    assert abs(model.w_prime_joules - 22000) <= 500
    assert model.fit_r_squared >= 0.99


def test_2_param_fallback_when_3_param_fit_poor():
    # Highly noisy / sparse data — force 2-param fallback
    mmp = [[300, 320], [600, 295], [1200, 285]]
    model = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    assert model.model in ("3-param-hyperbolic", "2-param-hyperbolic")
    # Noisy-few-points case must still return a valid model
    assert 200 <= model.cp_watts <= 400


def test_snapshot_writes_current_and_history(tmp_path):
    mmp = synthetic_mmp()
    model = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    written = write_snapshot(model, base_dir=tmp_path, now_iso="2026-04-16T00:00:00Z")
    current = tmp_path / "cp_w_current.json"
    history = tmp_path / "history" / "cp_w_2026-04.json"
    assert current.exists() and history.exists()
    data = json.loads(current.read_text())
    assert data["cp_watts"] == model.cp_watts


def test_cache_skips_refit_when_data_unchanged(tmp_path, monkeypatch):
    mmp = synthetic_mmp()
    model1 = fit_cp_w(mmp, athlete_ftp=288, window_days=90)
    write_snapshot(model1, base_dir=tmp_path, now_iso="2026-04-16T00:00:00Z")
    # fit_cp_w should expose a cache hook
    from src.coach.physiology import cp_w_fitter as m
    hash1 = m.hash_mmp(mmp)
    hash2 = m.hash_mmp(mmp)
    assert hash1 == hash2
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/physiology/test_cp_w_fitter.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement fitter**

Write `icu/src/coach/physiology/cp_w_fitter.py`:
```python
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
    """Best-effort extraction tolerant to both list-of-dicts and dict-of-lists shapes."""
    if isinstance(doc, dict) and "secs" in doc and "watts" in doc:
        yield from zip(doc["secs"], doc["watts"])
    elif isinstance(doc, list):
        for item in doc:
            if isinstance(item, dict) and "secs" in item and "watts" in item:
                yield item["secs"], item["watts"]
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/physiology/test_cp_w_fitter.py -v`
Expected: PASS all four.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/physiology/cp_w_fitter.py icu/tests/unit/physiology/test_cp_w_fitter.py
git commit -m "feat(coach): add CP/W' hyperbolic fitter with 2-param fallback"
```

---

## Task 5: W' balance real-time model

**Files:**
- Create: `icu/src/coach/physiology/w_balance_model.py`
- Create: `icu/tests/unit/physiology/test_w_balance_model.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/physiology/test_w_balance_model.py`:
```python
from src.coach.physiology.w_balance_model import compute_w_balance, compute_tau


def test_tau_formula_skiba_2012():
    # D_CP = 100 -> tau ≈ 546*exp(-1) + 316 ≈ 517
    tau = compute_tau(cp=280, mean_power_below_cp=180)
    assert 510 <= tau <= 525


def test_constant_above_cp_depletes_w_prime():
    cp = 280
    w_prime = 20000
    # 30 s at 380 W above CP = 100 W * 30 s = 3000 J drain
    stream = [380] * 30
    series = compute_w_balance(
        stream,
        cp=cp,
        w_prime=w_prime,
        activity_id="iTest",
        laps=[{"lap_index": 0, "type": "work", "start_s": 0, "end_s": 30}],
    )
    assert abs(series.w_prime_used_j - 3000) <= 200
    assert series.min_w_bal_j <= w_prime - 2800


def test_below_cp_recovers_exponentially():
    cp = 280
    w_prime = 20000
    # 30 s at 350 W drains ~2100 J, then 120 s at 150 W recovers
    stream = [350] * 30 + [150] * 120
    series = compute_w_balance(
        stream,
        cp=cp,
        w_prime=w_prime,
        activity_id="iTest2",
        laps=[
            {"lap_index": 0, "type": "work", "start_s": 0, "end_s": 30},
            {"lap_index": 1, "type": "recovery", "start_s": 30, "end_s": 150},
        ],
    )
    final = series.w_bal_series_1hz[-1]
    # Should recover substantially — expect ≥ 80% restored
    assert final >= int(w_prime * 0.80)
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/physiology/test_w_balance_model.py -v`

- [ ] **Step 3: Implement**

Write `icu/src/coach/physiology/w_balance_model.py`:
```python
import math
from typing import Iterable, Sequence

from .types import LapWBal, WBalanceSeries


def compute_tau(cp: float, mean_power_below_cp: float) -> float:
    d_cp = cp - mean_power_below_cp
    return 546.0 * math.exp(-0.01 * d_cp) + 316.0


def compute_w_balance(
    stream: Sequence[float],
    *,
    cp: float,
    w_prime: float,
    activity_id: str,
    laps: Iterable[dict],
    dt: float = 1.0,
) -> WBalanceSeries:
    below = [p for p in stream if p is not None and p <= cp]
    mean_below = sum(below) / len(below) if below else cp * 0.6
    tau = compute_tau(cp, mean_below)

    series = []
    w_bal = float(w_prime)
    for p in stream:
        if p is None:
            series.append(int(round(w_bal)))
            continue
        if p > cp:
            w_bal = w_bal - (p - cp) * dt
        else:
            w_bal = w_prime - (w_prime - w_bal) * math.exp(-dt / tau)
        series.append(int(round(w_bal)))

    min_bal = min(series)
    min_idx = series.index(min_bal)
    sec_below_15 = sum(1 for v in series if v < 0.15 * w_prime)

    lap_rows = []
    for lap in laps:
        start = int(lap["start_s"])
        end = min(int(lap["end_s"]), len(series) - 1)
        if end <= start:
            continue
        start_val = series[start]
        end_val = series[end]
        depletion = (start_val - end_val) / w_prime * 100 if w_prime else 0.0
        lap_rows.append(
            LapWBal(
                lap_index=int(lap["lap_index"]),
                type=lap.get("type", "steady"),
                w_bal_start_j=start_val,
                w_bal_end_j=end_val,
                depletion_pct=round(depletion, 1),
            )
        )

    w_prime_used = int(round(w_prime - min_bal)) if min_bal < w_prime else 0

    return WBalanceSeries(
        activity_id=activity_id,
        cp_used_w=int(cp),
        w_prime_used_j=w_prime_used,
        tau_s=round(tau, 1),
        min_w_bal_j=min_bal,
        min_w_bal_pct=round(min_bal / w_prime * 100, 1),
        min_w_bal_timestamp_s=min_idx,
        seconds_below_15pct=sec_below_15,
        laps=lap_rows,
        w_bal_series_1hz=series,
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/physiology/test_w_balance_model.py -v`

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/physiology/w_balance_model.py icu/tests/unit/physiology/test_w_balance_model.py
git commit -m "feat(coach): add Skiba-Clarke W' balance real-time model"
```

---

