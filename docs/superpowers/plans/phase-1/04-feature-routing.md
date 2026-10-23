# Phase 1 — Feature detection and relevance routing (Tasks 9-10)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

## Task 9: Feature detector

**Files:**
- Create: `icu/src/coach/deep_analyzer/feature_detector.py`
- Create: `icu/tests/unit/deep_analyzer/test_feature_detector.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_feature_detector.py`:
```python
from src.coach.deep_analyzer.feature_detector import detect_features


def _activity(**overrides):
    base = {
        "id": "i1",
        "type": "Ride",
        "duration_s": 3600,
        "total_kj": 800,
        "elevation_gain_m": 150,
        "np_watts": 220,
        "max_hr": 170,
        "decoupling_pct": 4,
        "hr_drift_z2_bpm": 2,
        "avg_temperature_c": 22,
        "laps": [],
    }
    base.update(overrides)
    return base


def test_race_flag_by_type():
    f = detect_features(_activity(type="Race"), streams=None, physiology=None, athlete={"hr_max": 195})
    assert f.is_race is True


def test_race_flag_by_np_hr_combo_uses_cp():
    activity = _activity(np_watts=280, max_hr=190)
    physiology = {"cp_watts": 290}
    f = detect_features(activity, streams=None, physiology=physiology, athlete={"hr_max": 195})
    assert f.is_race is True


def test_intervals_detected_from_lap_if():
    activity = _activity(laps=[
        {"duration_s": 240, "if": 1.05},
        {"duration_s": 240, "if": 0.55},
        {"duration_s": 240, "if": 1.05},
    ])
    f = detect_features(activity, streams=None, physiology=None, athlete={"hr_max": 195})
    assert f.has_intervals is True


def test_heat_stress_requires_temp_present():
    f = detect_features(_activity(avg_temperature_c=None), streams=None, physiology=None, athlete={"hr_max": 195})
    assert f.heat_stress is False
    f2 = detect_features(_activity(avg_temperature_c=31), streams=None, physiology=None, athlete={"hr_max": 195})
    assert f2.heat_stress is True


def test_w_prime_depleted_reads_physiology():
    f = detect_features(_activity(), streams=None, physiology={"min_w_bal_pct": 10}, athlete={"hr_max": 195})
    assert f.w_prime_depleted is True
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/feature_detector.py`:
```python
from typing import Optional

from .types import Features


def detect_features(
    activity: dict,
    streams: Optional[dict],
    physiology: Optional[dict],
    athlete: dict,
) -> Features:
    hr_max = int(athlete.get("hr_max") or 0) or None
    cp = None
    if physiology:
        cp = physiology.get("cp_watts")

    is_race = (activity.get("type", "").lower() == "race")
    if not is_race and cp and hr_max:
        np = activity.get("np_watts") or 0
        mhr = activity.get("max_hr") or 0
        if np > 0.95 * cp and mhr > 0.95 * hr_max:
            is_race = True

    laps = activity.get("laps") or []
    has_intervals = any(
        (l.get("if") or 0) > 0.85 and 30 <= (l.get("duration_s") or 0) <= 600
        for l in laps
    )

    elev = activity.get("elevation_gain_m") or 0
    has_climbing = elev > 300
    # sustained gradient check uses streams if provided
    if streams and "gradient" in streams:
        grades = streams["gradient"]
        run = 0
        for g in grades:
            if g is not None and g > 5:
                run += 1
                if run > 180:
                    has_climbing = True
                    break
            else:
                run = 0

    duration_s = int(activity.get("duration_s") or 0)
    is_endurance_long = duration_s > 7200

    if_val = max((l.get("if") or 0) for l in laps) if laps else (activity.get("if") or 0)
    decoupling = activity.get("decoupling_pct")
    hr_drift_z2 = activity.get("hr_drift_z2_bpm") or 0
    has_anomaly = (
        if_val > 0.90
        or (decoupling is not None and decoupling > 8)
        or hr_drift_z2 > 10
    )

    target_type = activity.get("planned_type") or None
    if not target_type and activity.get("type"):
        t = activity["type"].lower()
        if t in ("vo2max", "threshold", "tempo", "aerobic", "neuromuscular", "race"):
            target_type = t

    w_prime_depleted = bool(physiology and (physiology.get("min_w_bal_pct") or 100) < 20)

    temp = activity.get("avg_temperature_c")
    heat_stress = temp is not None and temp > 28

    return Features(
        has_intervals=has_intervals,
        is_race=is_race,
        has_climbing=has_climbing,
        is_endurance_long=is_endurance_long,
        has_anomaly=has_anomaly,
        target_type_claimed=target_type,
        w_prime_depleted=w_prime_depleted,
        heat_stress=bool(heat_stress),
        duration_seconds=duration_s,
        total_kj=int(activity.get("total_kj") or 0),
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/feature_detector.py icu/tests/unit/deep_analyzer/test_feature_detector.py
git commit -m "feat(coach): add deep analyzer feature detector"
```

---

## Task 10: Relevance router

**Files:**
- Create: `icu/src/coach/deep_analyzer/router.py`
- Create: `icu/tests/unit/deep_analyzer/test_router.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_router.py`:
```python
from src.coach.deep_analyzer.router import route
from src.coach.deep_analyzer.types import Features


def test_race_activates_all_six():
    f = Features(duration_seconds=3600, total_kj=700, is_race=True)
    r = route(f)
    assert set(r.keys()) == {"pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"}
    assert all(score >= 0.5 for score in r.values())


def test_intervals_activates_pacing_and_wbal():
    f = Features(duration_seconds=3600, total_kj=500, has_intervals=True)
    r = route(f)
    assert r["pacing"] >= 0.5 and r["w_balance"] >= 0.5


def test_endurance_long_activates_durability():
    f = Features(duration_seconds=10800, total_kj=2800, is_endurance_long=True)
    r = route(f)
    assert r["durability"] >= 0.5


def test_plain_z2_only_historical():
    f = Features(duration_seconds=3600, total_kj=400)
    r = route(f)
    activated = [k for k, v in r.items() if v >= 0.5]
    assert activated == ["historical_cmp"]
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/router.py`:
```python
from .types import Features

SUB_ANALYZERS = ["pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"]
THRESHOLD = 0.5


def route(features: Features) -> dict[str, float]:
    if features.is_race:
        return {k: 1.0 for k in SUB_ANALYZERS}

    scores = {
        "pacing": 0.9 if features.has_intervals else 0.2,
        "w_balance": 0.95 if features.has_intervals else (0.9 if features.w_prime_depleted else 0.3),
        "durability": 0.9 if features.is_endurance_long else 0.4,
        "climbing": 0.9 if features.has_climbing else 0.1,
        "target_align": 0.85 if features.target_type_claimed else 0.3,
        "historical_cmp": 0.6,
    }
    return scores
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/router.py icu/tests/unit/deep_analyzer/test_router.py
git commit -m "feat(coach): add deep analyzer relevance router"
```

---

