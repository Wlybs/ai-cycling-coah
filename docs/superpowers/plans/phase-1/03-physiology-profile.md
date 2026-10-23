# Phase 1 — Physiology profile - durability, response, facade (Tasks 6-8)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

## Task 6: Durability curve

**Files:**
- Create: `icu/src/coach/physiology/durability_model.py`
- Create: `icu/tests/unit/physiology/test_durability_model.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/physiology/test_durability_model.py`:
```python
from src.coach.physiology.durability_model import fit_durability


def synthetic_ride(duration_s=10800, peak_w=400, decay_per_1000kj=0.05):
    # Power as rough function of cumulative kJ — used to generate checkpoints
    stream = []
    kj = 0.0
    for t in range(duration_s):
        p = peak_w * max(0.70, (1.0 - decay_per_1000kj * (kj / 1000)))
        stream.append(p)
        kj += p / 1000  # Watts / 1000 = kJ per second
    return {"activity_id": f"i{duration_s}", "power_stream": stream}


def test_fit_durability_decays_positively():
    rides = [synthetic_ride() for _ in range(5)]
    curve = fit_durability(rides)
    assert curve.sample_size_rides == 5
    assert curve.fresh_mmp_w["300s"] > 0
    # Decay rate must be non-negative (power drops or holds)
    for dur in ("60s", "300s", "1200s"):
        assert curve.decay_rate_pct_per_1000kj[dur] >= 0
    # 2500 kJ fatigued MMP must be <= fresh
    assert curve.fatigued_mmp_w["2500kj"]["300s"] <= curve.fresh_mmp_w["300s"]


def test_insufficient_data_returns_empty_curve():
    curve = fit_durability([])
    assert curve.sample_size_rides == 0
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/physiology/durability_model.py`:
```python
from datetime import datetime, timezone
from typing import List

from .types import DurabilityCurve

CHECKPOINTS_KJ = [500, 1500, 2000, 2500]
DURATIONS_S = [60, 300, 1200]


def _mmp_at_window(stream, start_idx, duration_s):
    end = start_idx + duration_s
    if end > len(stream):
        return None
    best = 0.0
    window_sum = sum(stream[start_idx:start_idx + duration_s])
    best = window_sum
    for i in range(start_idx + 1, end):
        window_sum += stream[i + duration_s - 1] if i + duration_s - 1 < len(stream) else 0
        window_sum -= stream[i - 1]
        if i + duration_s > len(stream):
            break
        best = max(best, window_sum)
    return best / duration_s


def _index_at_cumulative_kj(stream, target_kj):
    kj = 0.0
    for i, p in enumerate(stream):
        kj += (p or 0) / 1000.0
        if kj >= target_kj:
            return i
    return None


def fit_durability(rides: list) -> DurabilityCurve:
    if not rides:
        return DurabilityCurve(
            generated_at=datetime.now(timezone.utc).isoformat(),
            sample_size_rides=0,
            fresh_mmp_w={f"{d}s": 0 for d in DURATIONS_S},
            fatigued_mmp_w={f"{k}kj": {f"{d}s": 0 for d in DURATIONS_S} for k in CHECKPOINTS_KJ[1:]},
            decay_rate_pct_per_1000kj={f"{d}s": 0.0 for d in DURATIONS_S},
        )

    fresh_by_dur = {d: [] for d in DURATIONS_S}
    fatigued = {k: {d: [] for d in DURATIONS_S} for k in CHECKPOINTS_KJ[1:]}

    for ride in rides:
        stream = ride["power_stream"]
        fresh_idx = _index_at_cumulative_kj(stream, CHECKPOINTS_KJ[0])
        if fresh_idx is None:
            continue
        for d in DURATIONS_S:
            val = _mmp_at_window(stream, 0, d)
            if val is not None:
                fresh_by_dur[d].append(val)
        for kj_target in CHECKPOINTS_KJ[1:]:
            idx = _index_at_cumulative_kj(stream, kj_target)
            if idx is None:
                continue
            for d in DURATIONS_S:
                val = _mmp_at_window(stream, idx, d)
                if val is not None:
                    fatigued[kj_target][d].append(val)

    fresh_mmp = {f"{d}s": int(round(max(fresh_by_dur[d], default=0))) for d in DURATIONS_S}
    fatigued_out = {
        f"{k}kj": {
            f"{d}s": int(round(sum(fatigued[k][d]) / len(fatigued[k][d]))) if fatigued[k][d] else 0
            for d in DURATIONS_S
        }
        for k in CHECKPOINTS_KJ[1:]
    }
    decay = {}
    for d in DURATIONS_S:
        fresh_w = fresh_mmp[f"{d}s"] or 1
        fat_w = fatigued_out["2500kj"][f"{d}s"]
        delta_pct = max(0.0, (fresh_w - fat_w) / fresh_w * 100 / 2.5)
        decay[f"{d}s"] = round(delta_pct, 2)

    return DurabilityCurve(
        generated_at=datetime.now(timezone.utc).isoformat(),
        sample_size_rides=len(rides),
        fresh_mmp_w=fresh_mmp,
        fatigued_mmp_w=fatigued_out,
        decay_rate_pct_per_1000kj=decay,
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/physiology/durability_model.py icu/tests/unit/physiology/test_durability_model.py
git commit -m "feat(coach): add durability curve fitter with multi-kJ checkpoints"
```

---

## Task 7: Individual response profile

**Files:**
- Create: `icu/src/coach/physiology/response_profile.py`
- Create: `icu/tests/unit/physiology/test_response_profile.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/physiology/test_response_profile.py`:
```python
from src.coach.physiology.response_profile import build_profile, classify_tolerance


def test_classify_tolerance_rules():
    # Tiny HRV dip + tiny RHR bump → high
    assert classify_tolerance(next_day_hrv_delta_pct=-2.0, next_day_rhr_delta_bpm=1.0) == "high"
    # Moderate HRV hit → moderate
    assert classify_tolerance(next_day_hrv_delta_pct=-7.0, next_day_rhr_delta_bpm=4.0) == "moderate"
    # Big HRV drop → low
    assert classify_tolerance(next_day_hrv_delta_pct=-15.0, next_day_rhr_delta_bpm=8.0) == "low"


def test_build_profile_assigns_tolerance_and_knee_flag():
    sessions = [
        {"type": "vo2max", "date": "2026-04-10", "tss": 85, "if": 0.92, "planned_if": 0.95, "standing_climb_minutes": 6, "avg_hr_drift_bpm_standing": 4.0},
        {"type": "vo2max", "date": "2026-04-14", "tss": 90, "if": 0.93, "planned_if": 0.95, "standing_climb_minutes": 5, "avg_hr_drift_bpm_standing": 5.0},
    ]
    wellness = {
        "2026-04-11": {"hrv_delta_pct": -4, "rhr_delta_bpm": 2},
        "2026-04-15": {"hrv_delta_pct": -5, "rhr_delta_bpm": 3},
    }
    profile = build_profile(sessions=sessions, wellness_by_date=wellness, window_days=60)
    assert "vo2max" in profile.types
    assert profile.types["vo2max"].sessions_n == 2
    assert profile.types["vo2max"].tolerance_class in ("moderate", "high")
    assert profile.knee_loading.standing_climb_minutes_90d == 11
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/physiology/response_profile.py`:
```python
from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal

from .types import KneeLoading, ResponseProfile, ResponseTypeStats

MIN_RECOVERY_HOURS = {
    "aerobic": 12,
    "tempo": 24,
    "threshold": 36,
    "vo2max": 48,
    "neuromuscular": 36,
    "race": 72,
}


def classify_tolerance(
    next_day_hrv_delta_pct: float,
    next_day_rhr_delta_bpm: float,
) -> Literal["low", "moderate", "high"]:
    if next_day_hrv_delta_pct <= -10 or next_day_rhr_delta_bpm >= 7:
        return "low"
    if next_day_hrv_delta_pct <= -5 or next_day_rhr_delta_bpm >= 3:
        return "moderate"
    return "high"


def _next_day(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (d + timedelta(days=1)).isoformat()


def build_profile(
    sessions: Iterable[dict],
    wellness_by_date: dict,
    window_days: int = 60,
) -> ResponseProfile:
    per_type: dict[str, list] = {}
    knee_minutes = 0
    knee_hr_drifts = []

    for s in sessions:
        per_type.setdefault(s["type"], []).append(s)
        knee_minutes += int(s.get("standing_climb_minutes") or 0)
        if "avg_hr_drift_bpm_standing" in s:
            knee_hr_drifts.append(float(s["avg_hr_drift_bpm_standing"]))

    types_out: dict[str, ResponseTypeStats] = {}
    for t, items in per_type.items():
        avg_tss = sum(i["tss"] for i in items) / len(items)
        hrv_deltas = []
        rhr_deltas = []
        adherences = []
        for i in items:
            w = wellness_by_date.get(_next_day(i["date"]))
            if w:
                hrv_deltas.append(w.get("hrv_delta_pct", 0))
                rhr_deltas.append(w.get("rhr_delta_bpm", 0))
            if i.get("planned_if"):
                adherences.append(1 if abs(i["if"] - i["planned_if"]) <= 0.05 else 0)

        hrv_avg = sum(hrv_deltas) / len(hrv_deltas) if hrv_deltas else 0.0
        rhr_avg = sum(rhr_deltas) / len(rhr_deltas) if rhr_deltas else 0.0
        tolerance = classify_tolerance(hrv_avg, rhr_avg)

        types_out[t] = ResponseTypeStats(
            sessions_n=len(items),
            avg_tss=int(round(avg_tss)),
            next_day_hrv_delta_pct=round(hrv_avg, 2),
            next_day_rhr_delta_bpm=round(rhr_avg, 2),
            avg_target_adherence=round(sum(adherences) / len(adherences), 2) if adherences else 0.0,
            tolerance_class=tolerance,
            recommended_min_interval_hours=MIN_RECOVERY_HOURS.get(t, 24),
        )

    avg_drift = sum(knee_hr_drifts) / len(knee_hr_drifts) if knee_hr_drifts else 0.0
    flag = None
    if knee_minutes > 120 or avg_drift > 8:
        flag = "caution"
    elif knee_minutes > 60 or avg_drift > 5:
        flag = "watch"

    return ResponseProfile(
        generated_at=datetime.now(timezone.utc).isoformat(),
        window_days=window_days,
        types=types_out,
        knee_loading=KneeLoading(
            standing_climb_minutes_90d=knee_minutes,
            avg_hr_drift_bpm_standing=round(avg_drift, 1),
            flag=flag,
        ),
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/physiology/test_response_profile.py -v`

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/physiology/response_profile.py icu/tests/unit/physiology/test_response_profile.py
git commit -m "feat(coach): add individual response profile with knee-loading flag"
```

---

## Task 8: Physiology refresher facade

**Files:**
- Create: `icu/src/coach/physiology/refresher.py`
- Create: `icu/tests/unit/physiology/test_refresher.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/physiology/test_refresher.py`:
```python
import json
from pathlib import Path

from src.coach.physiology.refresher import refresh_all


def _seed_warehouse(base: Path):
    pd = base / "icu_data_warehouse" / "3_PowerData"
    pd.mkdir(parents=True)
    (pd / "power_curves_90d.json").write_text(json.dumps({
        "secs": [5, 30, 60, 300, 600, 1200],
        "watts": [1200, 780, 540, 340, 305, 290],
    }))
    (pd / "power_curves_all_time.json").write_text(json.dumps({
        "secs": [5, 30, 60, 300, 600, 1200],
        "watts": [1389, 850, 600, 360, 315, 295],
    }))
    profile = base / "icu_data_warehouse" / "1_Profile"
    profile.mkdir(parents=True)
    (profile / "athlete.json").write_text(json.dumps({
        "weight": 62, "ftp": 288, "hr_max": 195,
    }))


def test_refresh_all_writes_cp_w_snapshot_minimal(tmp_path):
    _seed_warehouse(tmp_path)
    result = refresh_all(
        warehouse_dir=tmp_path / "icu_data_warehouse",
        memory_dir=tmp_path / "coach_memory",
        activities=[],
        wellness_by_date={},
    )
    assert result["cp_w"]["status"] == "ok"
    assert (tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").exists()


def test_refresh_all_partial_failure_continues(tmp_path, monkeypatch):
    _seed_warehouse(tmp_path)

    # Break durability by passing ride with no power_stream key
    result = refresh_all(
        warehouse_dir=tmp_path / "icu_data_warehouse",
        memory_dir=tmp_path / "coach_memory",
        activities=[{"id": "bad"}],  # missing power_stream → skipped not crash
        wellness_by_date={},
    )
    # cp_w still OK even if durability is empty
    assert result["cp_w"]["status"] == "ok"
    assert result["durability"]["status"] in ("ok", "empty")
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/physiology/refresher.py`:
```python
import json
import time
from pathlib import Path
from typing import Iterable, Optional

from ..common.logging import get_logger
from . import cp_w_fitter, durability_model, response_profile

LOG = get_logger("physiology_refresher")


def _load_athlete(warehouse_dir: Path) -> dict:
    path = warehouse_dir / "1_Profile" / "athlete.json"
    if not path.exists():
        return {"ftp": 288, "hr_max": 195, "weight": 62}
    return json.loads(path.read_text())


def _safe(name, fn):
    t0 = time.monotonic()
    try:
        fn()
        LOG.event(action=f"refresh_{name}", duration_ms=int((time.monotonic() - t0) * 1000), status="ok")
        return {"status": "ok"}
    except Exception as e:
        LOG.event(action=f"refresh_{name}", duration_ms=int((time.monotonic() - t0) * 1000), status="error", error=str(e))
        return {"status": "error", "error": str(e)}


def refresh_all(
    warehouse_dir: Path,
    memory_dir: Path,
    activities: Iterable[dict],
    wellness_by_date: dict,
) -> dict:
    warehouse_dir = Path(warehouse_dir)
    memory_dir = Path(memory_dir)
    physiology_dir = memory_dir / "physiology"
    physiology_dir.mkdir(parents=True, exist_ok=True)
    athlete = _load_athlete(warehouse_dir)
    ftp = int(athlete.get("ftp") or 288)

    result: dict = {}

    def fit_cp():
        mmp = cp_w_fitter.load_mmp_from_warehouse(warehouse_dir)
        if not mmp:
            raise RuntimeError("no MMP data available")
        model = cp_w_fitter.fit_cp_w(mmp, athlete_ftp=ftp, window_days=90)
        from datetime import datetime, timezone
        cp_w_fitter.write_snapshot(model, physiology_dir, now_iso=datetime.now(timezone.utc).isoformat())

    result["cp_w"] = _safe("cp_w", fit_cp)

    def fit_dur():
        rides = [a for a in activities if "power_stream" in a]
        curve = durability_model.fit_durability(rides)
        (physiology_dir / "durability.json").write_text(curve.model_dump_json(indent=2))

    result["durability"] = _safe("durability", fit_dur)
    if not list(activities):
        result["durability"] = {"status": "empty"}

    def fit_resp():
        profile = response_profile.build_profile(
            sessions=activities,
            wellness_by_date=wellness_by_date,
            window_days=60,
        )
        (physiology_dir / "response_profile.json").write_text(profile.model_dump_json(indent=2))

    result["response"] = _safe("response_profile", fit_resp)
    return result
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/physiology/refresher.py icu/tests/unit/physiology/test_refresher.py
git commit -m "feat(coach): add physiology refresher facade with per-step soft-fail"
```

---

