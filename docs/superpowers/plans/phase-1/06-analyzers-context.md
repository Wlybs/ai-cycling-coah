# Phase 1 — Context analyzers - climbing, target_align, historical_cmp (Tasks 14-16)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

## Task 14: Sub-analyzer — climbing

**Files:**
- Create: `icu/src/coach/deep_analyzer/sub_analyzers/climbing.py`
- Create: `icu/tests/unit/deep_analyzer/test_climbing.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_climbing.py`:
```python
from src.coach.deep_analyzer.sub_analyzers.climbing import analyze


def test_segments_climb_and_computes_wkg():
    streams = {
        "power": [320] * 600,
        "gradient": [6] * 600,
        "cadence": [82] * 600,
        "hr": [165] * 600,
        "altitude": list(range(0, 600)),
    }
    activity = {"id": "iClimb", "weight_kg": 62}
    findings = analyze(activity, streams=streams, physiology={"cp_watts": 280})
    c = findings.metrics["climbs"][0]
    assert abs(c["avg_power_w"] - 320) <= 2
    assert 5.1 <= c["avg_wkg"] <= 5.3
    assert c["vam_mh"] > 0


def test_standing_inference_low_cadence_high_power():
    streams = {
        "power": [340] * 600,
        "gradient": [7] * 600,
        "cadence": [65] * 600,
        "hr": [170] * 600,
        "altitude": list(range(0, 1200, 2)),
    }
    activity = {"id": "iStand", "weight_kg": 62}
    findings = analyze(activity, streams=streams, physiology={"cp_watts": 280})
    assert findings.metrics["standing_minutes"] >= 8
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/sub_analyzers/climbing.py`:
```python
from ..types import Findings

CLIMB_GRADE_PCT = 3.0
MIN_CLIMB_S = 180


def _segment_climbs(gradient, power, altitude):
    climbs = []
    start = None
    for i, g in enumerate(gradient):
        if g is not None and g >= CLIMB_GRADE_PCT:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= MIN_CLIMB_S:
                climbs.append((start, i))
            start = None
    if start is not None and len(gradient) - start >= MIN_CLIMB_S:
        climbs.append((start, len(gradient)))
    return climbs


def analyze(activity: dict, streams: dict, physiology: dict | None) -> Findings:
    if not streams or "gradient" not in streams:
        return Findings(analyzer="climbing", metrics={"reason": "no gradient stream"}, verdict="数据不足", evidence=[])

    gradient = streams["gradient"]
    power = streams.get("power") or []
    cadence = streams.get("cadence") or []
    hr = streams.get("hr") or []
    altitude = streams.get("altitude") or []
    weight = float(activity.get("weight_kg") or 62)
    cp = (physiology or {}).get("cp_watts", 280)

    climb_rows = []
    standing_seconds = 0
    for start, end in _segment_climbs(gradient, power, altitude):
        dur = end - start
        seg_power = [p for p in power[start:end] if p is not None]
        seg_cadence = [c for c in cadence[start:end] if c is not None]
        seg_hr = [h for h in hr[start:end] if h is not None]
        avg_power = sum(seg_power) / len(seg_power) if seg_power else 0.0
        avg_hr = sum(seg_hr) / len(seg_hr) if seg_hr else 0.0
        avg_wkg = round(avg_power / weight, 2)
        d_alt = (altitude[end - 1] - altitude[start]) if len(altitude) >= end else 0
        vam = (d_alt / dur) * 3600 if dur > 0 else 0
        standing = sum(
            1 for p, c in zip(seg_power, seg_cadence)
            if p is not None and c is not None and c < 75 and p > cp * 1.1
        )
        standing_seconds += standing
        climb_rows.append({
            "duration_s": dur,
            "avg_power_w": round(avg_power, 1),
            "avg_hr_bpm": round(avg_hr, 1),
            "avg_wkg": avg_wkg,
            "vam_mh": int(round(vam)),
            "standing_seconds": standing,
        })

    if not climb_rows:
        return Findings(analyzer="climbing", metrics={"reason": "no sustained climb"}, verdict="数据不足", evidence=[])

    first_wkg = climb_rows[0]["avg_wkg"]
    last_wkg = climb_rows[-1]["avg_wkg"]
    if last_wkg >= first_wkg * 0.98:
        verdict = "爬坡表现超预期" if len(climb_rows) > 1 and last_wkg > first_wkg else "持平"
    elif last_wkg >= first_wkg * 0.92:
        verdict = "持平"
    else:
        verdict = "疲劳衰退显著"

    return Findings(
        analyzer="climbing",
        metrics={
            "climbs": climb_rows,
            "standing_minutes": round(standing_seconds / 60, 1),
            "first_climb_wkg": first_wkg,
            "last_climb_wkg": last_wkg,
        },
        verdict=verdict,
        evidence=[
            (f"{len(climb_rows)} 段持续爬坡，首段 {first_wkg} W/kg，末段 {last_wkg} W/kg", "climbs[]"),
            (f"摇车累计 {round(standing_seconds / 60, 1)} 分钟", "cadence<75 & power>1.1·CP"),
        ],
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/sub_analyzers/climbing.py icu/tests/unit/deep_analyzer/test_climbing.py
git commit -m "feat(coach): add climbing sub-analyzer with standing inference"
```

---

## Task 15: Sub-analyzer — target_align

**Files:**
- Create: `icu/src/coach/deep_analyzer/sub_analyzers/target_align.py`
- Create: `icu/tests/unit/deep_analyzer/test_target_align.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_target_align.py`:
```python
from src.coach.deep_analyzer.sub_analyzers.target_align import analyze, default_range


def test_default_range_vo2max():
    lo, hi = default_range("vo2max", cp=280)
    assert int(lo) == int(round(1.06 * 280))
    assert int(hi) == int(round(1.20 * 280))


def test_hit_when_time_in_zone_meets_threshold():
    activity = {
        "id": "iHit",
        "planned_type": "vo2max",
        "laps": [
            {"type": "work", "duration_s": 240, "avg_power": 320},
            {"type": "recovery", "duration_s": 120, "avg_power": 180},
            {"type": "work", "duration_s": 240, "avg_power": 320},
            {"type": "recovery", "duration_s": 120, "avg_power": 180},
            {"type": "work", "duration_s": 240, "avg_power": 320},
            {"type": "recovery", "duration_s": 120, "avg_power": 180},
            {"type": "work", "duration_s": 240, "avg_power": 320},
        ],
    }
    findings = analyze(activity, physiology={"cp_watts": 280})
    assert findings.verdict == "命中"


def test_miss_flags_coach_under_prescription_when_three_consecutive():
    activity = {
        "id": "iMiss",
        "planned_type": "vo2max",
        "laps": [{"type": "work", "duration_s": 300, "avg_power": 260}],
    }
    history = [{"type": "vo2max", "missed": True}, {"type": "vo2max", "missed": True}]
    findings = analyze(activity, physiology={"cp_watts": 280}, recent_misses=history)
    assert findings.metrics["under_prescription_flag"] is True
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/sub_analyzers/target_align.py`:
```python
from ..types import Findings

ZONES = {
    "vo2max": (1.06, 1.20, 12 * 60),
    "threshold": (0.95, 1.05, 20 * 60),
    "sweet-spot": (0.88, 0.94, 40 * 60),
    "tempo": (0.76, 0.88, 30 * 60),
    "aerobic": (0.56, 0.75, 45 * 60),
    "neuromuscular": (1.50, 3.00, 30),
}


def default_range(target_type: str, cp: int) -> tuple[float, float]:
    lo, hi, _ = ZONES.get(target_type, (0.95, 1.05, 20 * 60))
    return cp * lo, cp * hi


def analyze(activity: dict, physiology: dict | None, recent_misses: list | None = None) -> Findings:
    target = activity.get("planned_type")
    if not target or target not in ZONES:
        return Findings(analyzer="target_align", metrics={"reason": "no planned target"}, verdict="目标缺失", evidence=[])

    cp = (physiology or {}).get("cp_watts") or 0
    if not cp:
        return Findings(analyzer="target_align", metrics={"reason": "no CP"}, verdict="数据不足", evidence=[])

    lo, hi = default_range(target, cp)
    _, _, min_in_zone = ZONES[target]

    seconds_in_zone = 0
    for lap in activity.get("laps", []):
        if lap.get("type") != "work":
            continue
        p = lap.get("avg_power") or 0
        if lo <= p <= hi:
            seconds_in_zone += lap.get("duration_s") or 0

    hit = seconds_in_zone >= min_in_zone
    ratio = seconds_in_zone / min_in_zone if min_in_zone else 1.0

    if hit:
        verdict = "命中"
    elif ratio >= 0.5:
        verdict = "部分命中"
    else:
        verdict = "刺激错配"

    misses_prev = sum(1 for m in (recent_misses or []) if m.get("type") == target and m.get("missed"))
    under_flag = (not hit) and misses_prev >= 2

    return Findings(
        analyzer="target_align",
        metrics={
            "target_type": target,
            "target_range_w": [int(round(lo)), int(round(hi))],
            "seconds_in_zone": seconds_in_zone,
            "min_required_seconds": min_in_zone,
            "ratio_to_required": round(ratio, 2),
            "under_prescription_flag": under_flag,
        },
        verdict=verdict,
        evidence=[
            (f"目标类型 {target}；需求最少 {min_in_zone//60} 分钟在 {int(lo)}–{int(hi)} W", "ZONES table"),
            (f"实际累计 {seconds_in_zone//60} 分钟在区间内 (达成率 {ratio:.0%})", "laps[].avg_power 聚合"),
        ],
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/sub_analyzers/target_align.py icu/tests/unit/deep_analyzer/test_target_align.py
git commit -m "feat(coach): add target alignment sub-analyzer with under-prescription flag"
```

---

## Task 16: Sub-analyzer — historical_cmp

**Files:**
- Create: `icu/src/coach/deep_analyzer/sub_analyzers/historical_cmp.py`
- Create: `icu/tests/unit/deep_analyzer/test_historical_cmp.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_historical_cmp.py`:
```python
from src.coach.deep_analyzer.sub_analyzers.historical_cmp import analyze


def test_progression_detected():
    current = {"id": "iNow", "type": "vo2max", "duration_s": 3600, "np_watts": 290, "decoupling_pct": 3}
    history = [
        {"id": "i1", "type": "vo2max", "duration_s": 3400, "np_watts": 275, "decoupling_pct": 5},
        {"id": "i2", "type": "vo2max", "duration_s": 3500, "np_watts": 272, "decoupling_pct": 5},
        {"id": "i3", "type": "vo2max", "duration_s": 3800, "np_watts": 270, "decoupling_pct": 6},
    ]
    findings = analyze(current, history=history)
    assert findings.verdict in ("进步", "持平")


def test_regression_detected():
    current = {"id": "iNow", "type": "vo2max", "duration_s": 3600, "np_watts": 250, "decoupling_pct": 9}
    history = [
        {"id": "i1", "type": "vo2max", "duration_s": 3600, "np_watts": 290, "decoupling_pct": 4},
        {"id": "i2", "type": "vo2max", "duration_s": 3500, "np_watts": 285, "decoupling_pct": 5},
        {"id": "i3", "type": "vo2max", "duration_s": 3700, "np_watts": 292, "decoupling_pct": 4},
    ]
    findings = analyze(current, history=history)
    assert findings.verdict == "退步"


def test_few_comparables_lowers_confidence():
    current = {"id": "iNow", "type": "threshold", "duration_s": 3600, "np_watts": 280, "decoupling_pct": 5}
    history = [{"id": "i1", "type": "threshold", "duration_s": 3600, "np_watts": 275, "decoupling_pct": 5}]
    findings = analyze(current, history=history)
    assert findings.metrics["confidence"] in ("low", "tentative")
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/sub_analyzers/historical_cmp.py`:
```python
from ..types import Findings


def _similar(current, candidate, tol=0.20):
    if candidate.get("type") != current.get("type"):
        return False
    d1 = current.get("duration_s", 0)
    d2 = candidate.get("duration_s", 0)
    if d1 == 0:
        return False
    return abs(d1 - d2) / d1 <= tol


def analyze(current: dict, history: list) -> Findings:
    comps = [h for h in (history or []) if _similar(current, h)]
    n = len(comps)
    if n == 0:
        return Findings(analyzer="historical_cmp", metrics={"reason": "no comparables"}, verdict="数据不足", evidence=[])

    conf = "low" if n < 3 else "moderate"
    if n >= 5:
        conf = "high"

    avg_np = sum(c.get("np_watts") or 0 for c in comps) / n
    avg_dec = sum(c.get("decoupling_pct") or 0 for c in comps) / n
    cur_np = current.get("np_watts") or 0
    cur_dec = current.get("decoupling_pct") or 0
    np_delta_pct = (cur_np - avg_np) / avg_np * 100 if avg_np else 0

    if np_delta_pct >= 3 and cur_dec <= avg_dec:
        verdict = "进步"
    elif np_delta_pct <= -3 or cur_dec > avg_dec + 2:
        verdict = "退步"
    else:
        verdict = "持平"

    return Findings(
        analyzer="historical_cmp",
        metrics={
            "comparables_n": n,
            "avg_np_w": int(round(avg_np)),
            "cur_np_w": cur_np,
            "np_delta_pct": round(np_delta_pct, 1),
            "avg_decoupling_pct": round(avg_dec, 2),
            "cur_decoupling_pct": cur_dec,
            "confidence": conf,
        },
        verdict=verdict,
        evidence=[
            (f"与近 90 天 {n} 次相似 {current.get('type')} 对比，NP 变化 {np_delta_pct:+.1f}%", "history filtered by type+duration±20%"),
            (f"解耦 {cur_dec:.1f}% vs 历史均值 {avg_dec:.1f}%", "current.decoupling_pct"),
        ],
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/sub_analyzers/historical_cmp.py icu/tests/unit/deep_analyzer/test_historical_cmp.py
git commit -m "feat(coach): add historical-comparison sub-analyzer"
```

---

