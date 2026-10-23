# Phase 1 — Intra-session analyzers - pacing, W balance, durability (Tasks 11-13)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

## Task 11: Sub-analyzer — pacing

**Files:**
- Create: `icu/src/coach/deep_analyzer/sub_analyzers/pacing.py`
- Create: `icu/tests/unit/deep_analyzer/test_pacing.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_pacing.py`:
```python
from src.coach.deep_analyzer.sub_analyzers.pacing import analyze


def test_front_loaded_detected():
    activity = {
        "id": "i1",
        "laps": [
            {"lap_index": 0, "avg_power": 330, "np_power": 345, "duration_s": 300, "type": "work"},
            {"lap_index": 1, "avg_power": 320, "np_power": 330, "duration_s": 300, "type": "work"},
            {"lap_index": 2, "avg_power": 295, "np_power": 305, "duration_s": 300, "type": "work"},
            {"lap_index": 3, "avg_power": 260, "np_power": 270, "duration_s": 300, "type": "work"},
        ],
    }
    findings = analyze(activity, physiology={"cp_watts": 280, "w_prime_joules": 22000})
    assert findings.verdict in ("起步冒进", "后段崩盘")
    assert any("VI" in e[0] or "功率" in e[0] for e in findings.evidence)


def test_steady_pacing_verdict():
    activity = {
        "id": "i2",
        "laps": [
            {"lap_index": i, "avg_power": 300, "np_power": 305, "duration_s": 300, "type": "work"}
            for i in range(4)
        ],
    }
    findings = analyze(activity, physiology={"cp_watts": 280, "w_prime_joules": 22000})
    assert findings.verdict in ("节奏平稳", "均衡分布")
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/sub_analyzers/pacing.py`:
```python
from ..types import Findings


def _vi(lap):
    ap = lap.get("avg_power") or 0
    np = lap.get("np_power") or ap
    return round(np / ap, 3) if ap else 1.0


def analyze(activity: dict, physiology: dict | None = None) -> Findings:
    laps = [l for l in activity.get("laps", []) if l.get("type") == "work"]
    if len(laps) < 2:
        return Findings(
            analyzer="pacing",
            metrics={"reason": "insufficient work laps"},
            verdict="数据不足",
            evidence=[],
        )

    vis = [_vi(l) for l in laps]
    vi_mean = round(sum(vis) / len(vis), 3)
    rest = vis[1:]
    rest_mean = sum(rest) / len(rest) if rest else vi_mean
    break_idx = next((i + 1 for i, v in enumerate(vis[1:]) if v > rest_mean + 0.10), None)

    n = len(laps)
    third = max(1, n // 3)
    avg_first = sum(l["avg_power"] for l in laps[:third]) / third
    avg_last = sum(l["avg_power"] for l in laps[-third:]) / third
    delta_pct = (avg_first - avg_last) / avg_first * 100 if avg_first else 0

    if delta_pct > 10:
        verdict = "起步冒进"
    elif delta_pct < -10:
        verdict = "后段崩盘"
    elif abs(delta_pct) <= 3:
        verdict = "节奏平稳"
    else:
        verdict = "均衡分布"

    return Findings(
        analyzer="pacing",
        metrics={
            "vi_mean": vi_mean,
            "first_third_avg_w": int(round(avg_first)),
            "last_third_avg_w": int(round(avg_last)),
            "front_to_back_delta_pct": round(delta_pct, 1),
            "pacing_break_lap_index": break_idx,
        },
        verdict=verdict,
        evidence=[
            (f"前1/3平均 {int(avg_first)}W 对比后1/3 {int(avg_last)}W，差值 {delta_pct:+.1f}%", f"laps[0..{third-1}] vs laps[-{third}:]"),
            (f"整体 VI 均值 {vi_mean}", "per-lap NP/AP"),
        ],
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/sub_analyzers/pacing.py icu/tests/unit/deep_analyzer/test_pacing.py
git commit -m "feat(coach): add pacing sub-analyzer"
```

---

## Task 12: Sub-analyzer — w_balance

**Files:**
- Create: `icu/src/coach/deep_analyzer/sub_analyzers/w_balance.py`
- Create: `icu/tests/unit/deep_analyzer/test_wbalance_sub.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_wbalance_sub.py`:
```python
from src.coach.deep_analyzer.sub_analyzers.w_balance import analyze


def test_missing_wbal_returns_insufficient():
    findings = analyze({"id": "iX"}, physiology={"cp_watts": 280, "w_prime_joules": 22000}, wbal_series=None)
    assert findings.verdict == "数据不足"


def test_reads_lap_depletions():
    wbal = {
        "min_w_bal_pct": 22,
        "seconds_below_15pct": 0,
        "laps": [
            {"lap_index": 0, "type": "work", "depletion_pct": 30},
            {"lap_index": 1, "type": "recovery", "depletion_pct": -18},
            {"lap_index": 2, "type": "work", "depletion_pct": 40},
        ],
    }
    findings = analyze({"id": "iY"}, physiology={"cp_watts": 280, "w_prime_joules": 22000}, wbal_series=wbal)
    assert findings.metrics["max_lap_depletion_pct"] == 40
    assert findings.verdict in ("W' 管理得当", "W' 管理失衡", "过度依赖 W' 债务")


def test_over_leveraged_verdict():
    wbal = {
        "min_w_bal_pct": 8,
        "seconds_below_15pct": 240,
        "laps": [
            {"lap_index": 0, "type": "work", "depletion_pct": 70},
            {"lap_index": 1, "type": "recovery", "depletion_pct": -5},
        ],
    }
    findings = analyze({"id": "iZ"}, physiology={"cp_watts": 280, "w_prime_joules": 22000}, wbal_series=wbal)
    assert findings.verdict == "过度依赖 W' 债务"
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/sub_analyzers/w_balance.py`:
```python
from ..types import Findings


def analyze(activity: dict, physiology: dict | None, wbal_series: dict | None) -> Findings:
    if wbal_series is None:
        return Findings(
            analyzer="w_balance",
            metrics={"reason": "no W' balance series available"},
            verdict="数据不足",
            evidence=[],
        )

    work_laps = [l for l in wbal_series["laps"] if l["type"] == "work"]
    recov_laps = [l for l in wbal_series["laps"] if l["type"] == "recovery"]
    max_dep = max((l["depletion_pct"] for l in work_laps), default=0.0)
    avg_recov_pct = (
        sum(abs(l["depletion_pct"]) for l in recov_laps) / len(recov_laps)
        if recov_laps else 0.0
    )
    min_pct = wbal_series.get("min_w_bal_pct", 100)
    sec_below_15 = wbal_series.get("seconds_below_15pct", 0)

    if min_pct < 15 or sec_below_15 > 60:
        verdict = "过度依赖 W' 债务"
    elif max_dep > 60 and avg_recov_pct < 50:
        verdict = "W' 管理失衡"
    else:
        verdict = "W' 管理得当"

    return Findings(
        analyzer="w_balance",
        metrics={
            "max_lap_depletion_pct": round(max_dep, 1),
            "avg_recovery_restore_pct": round(avg_recov_pct, 1),
            "min_w_bal_pct": round(min_pct, 1),
            "seconds_below_15pct": sec_below_15,
        },
        verdict=verdict,
        evidence=[
            (f"最低 W'bal {min_pct:.1f}% ；低于15%累计 {sec_below_15}s", "w_balance_model output"),
            (f"最大区间消耗 {max_dep:.1f}% ；平均恢复回升 {avg_recov_pct:.1f}%", "laps[].depletion_pct"),
        ],
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/sub_analyzers/w_balance.py icu/tests/unit/deep_analyzer/test_wbalance_sub.py
git commit -m "feat(coach): add W' balance sub-analyzer"
```

---

## Task 13: Sub-analyzer — durability

**Files:**
- Create: `icu/src/coach/deep_analyzer/sub_analyzers/durability.py`
- Create: `icu/tests/unit/deep_analyzer/test_durability_sub.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_durability_sub.py`:
```python
from src.coach.deep_analyzer.sub_analyzers.durability import analyze


def test_below_baseline_flags_deficit():
    personal = {
        "fresh_mmp_w": {"300s": 350},
        "fatigued_mmp_w": {
            "1500kj": {"300s": 330},
            "2000kj": {"300s": 320},
            "2500kj": {"300s": 310},
        },
    }
    ride = {"id": "iA", "total_kj": 2600, "fatigued_mmp_w": {"1500kj": {"300s": 300}}}
    findings = analyze(ride, personal_curve=personal)
    assert findings.metrics["durability_deficit_pct_300s"] > 0
    assert "deficit" in str(findings.metrics).lower() or findings.verdict == "疲劳衰退显著"


def test_above_baseline_shows_bonus():
    personal = {
        "fresh_mmp_w": {"300s": 330},
        "fatigued_mmp_w": {
            "1500kj": {"300s": 310}, "2000kj": {"300s": 300}, "2500kj": {"300s": 290},
        },
    }
    ride = {"id": "iB", "total_kj": 2800, "fatigued_mmp_w": {"2500kj": {"300s": 310}}}
    findings = analyze(ride, personal_curve=personal)
    assert findings.verdict == "爬坡表现超预期"


def test_short_ride_returns_insufficient():
    ride = {"id": "iC", "total_kj": 400, "fatigued_mmp_w": {}}
    findings = analyze(ride, personal_curve={"fresh_mmp_w": {"300s": 330}, "fatigued_mmp_w": {}})
    assert findings.verdict == "数据不足"
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/sub_analyzers/durability.py`:
```python
from ..types import Findings

CHECKPOINTS = ["1500kj", "2000kj", "2500kj"]


def analyze(ride: dict, personal_curve: dict | None) -> Findings:
    if ride.get("total_kj", 0) < 1500:
        return Findings(
            analyzer="durability",
            metrics={"reason": "ride shorter than 1500 kJ"},
            verdict="数据不足",
            evidence=[],
        )
    if not personal_curve or not personal_curve.get("fresh_mmp_w"):
        return Findings(
            analyzer="durability",
            metrics={"reason": "no personal curve"},
            verdict="数据不足",
            evidence=[],
        )

    ride_fat = ride.get("fatigued_mmp_w") or {}
    best_delta_pct = None
    best_checkpoint = None
    for cp in CHECKPOINTS:
        if cp not in ride_fat:
            continue
        for dur in ("300s",):
            ride_w = ride_fat[cp].get(dur)
            base_w = personal_curve["fatigued_mmp_w"].get(cp, {}).get(dur)
            if ride_w and base_w:
                delta_pct = (ride_w - base_w) / base_w * 100
                if best_delta_pct is None or abs(delta_pct) > abs(best_delta_pct):
                    best_delta_pct = delta_pct
                    best_checkpoint = cp

    if best_delta_pct is None:
        return Findings(
            analyzer="durability",
            metrics={"reason": "no overlapping checkpoints"},
            verdict="数据不足",
            evidence=[],
        )

    if best_delta_pct >= 3:
        verdict = "爬坡表现超预期"
    elif best_delta_pct <= -5:
        verdict = "疲劳衰退显著"
    else:
        verdict = "持平"

    metrics = {
        "best_checkpoint": best_checkpoint,
        "durability_bonus_pct_300s": round(best_delta_pct, 1) if best_delta_pct > 0 else 0.0,
        "durability_deficit_pct_300s": round(-best_delta_pct, 1) if best_delta_pct < 0 else 0.0,
    }
    return Findings(
        analyzer="durability",
        metrics=metrics,
        verdict=verdict,
        evidence=[
            (f"在 {best_checkpoint} 检查点，5min MMP 相对个人基线 {best_delta_pct:+.1f}%", f"ride.fatigued_mmp_w[{best_checkpoint}]"),
        ],
    )
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/sub_analyzers/durability.py icu/tests/unit/deep_analyzer/test_durability_sub.py
git commit -m "feat(coach): add durability sub-analyzer"
```

---

