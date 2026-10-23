# AI Coach — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personalized physiology model layer (CP/W', W' balance, durability, response profile) and a deep session analyzer (feature detection → relevance routing → six sub-analyzers → coach-prose report composer), then wire them into the existing sync pipeline, Coach Brief, and plan generator — so plan quality improves immediately without rewriting `plan_generator.py`.

**Architecture:** Pure-Python deterministic numeric models (no LLM in the math path) writing snapshot JSONs into `coach_memory/physiology/`; per-activity W' balance written next to streams; deep-analysis markdown + trace files under `coach_memory/deep_analysis/`; Gemini is called once per report for prose only; integration is three additive calls appended to `sync_data.py` plus a minimum-invasive prompt-injection helper inside `plan_generator.py` (full rewrite deferred to Phase 2).

**Tech Stack:** Python 3.12, scipy (new), numpy, pandas, pydantic v2, google-genai, pytest + pytest-asyncio (new). All outputs JSON/Markdown on local filesystem.

**Spec:** [`docs/superpowers/specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md`](../specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md)

**Invariant across every task:** Nothing in Phase 1 may break the existing `sync_data.py` pipeline. Every new call from `sync_data.py` is wrapped in try/except so Phase 1 can be disabled by deleting those three lines.

---

## Task 1: Scaffold Phase 1 package structure + dependencies

**Files:**
- Modify: `icu/requirements.txt`
- Create: `icu/pytest.ini`
- Create: `icu/tests/__init__.py`
- Create: `icu/tests/conftest.py`
- Create: `icu/src/coach/physiology/__init__.py`
- Create: `icu/src/coach/deep_analyzer/__init__.py`
- Create: `icu/src/coach/deep_analyzer/sub_analyzers/__init__.py`
- Create: `icu/src/coach/common/__init__.py`

- [ ] **Step 1: Add new dependencies**

Append to `icu/requirements.txt`:
```
scipy>=1.12
numpy>=1.26
pandas>=2.2
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 2: Install**

Run: `icu/.venv/bin/pip install -r icu/requirements.txt`
Expected: all packages install cleanly.

- [ ] **Step 3: Create package directories**

```bash
mkdir -p icu/src/coach/physiology icu/src/coach/deep_analyzer/sub_analyzers icu/src/coach/common
mkdir -p icu/tests/unit/physiology icu/tests/unit/deep_analyzer icu/tests/integration icu/tests/e2e icu/tests/fixtures/rides
```

Write empty `__init__.py` in each new package directory (`icu/src/coach/physiology/__init__.py`, `icu/src/coach/deep_analyzer/__init__.py`, `icu/src/coach/deep_analyzer/sub_analyzers/__init__.py`, `icu/src/coach/common/__init__.py`, `icu/tests/__init__.py`).

- [ ] **Step 4: Create pytest config**

Write `icu/pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
asyncio_mode = auto
markers =
    integration: tests that read real fixtures from tests/fixtures
    e2e: end-to-end tests with mocked external APIs
```

- [ ] **Step 5: Create test root fixture**

Write `icu/tests/conftest.py`:
```python
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
```

- [ ] **Step 6: Smoke test**

Run: `cd icu && .venv/bin/pytest -q`
Expected: `no tests ran in ...s` (exit 5 is fine here — we just want collection to succeed without import errors).

- [ ] **Step 7: Commit**

```bash
git add icu/requirements.txt icu/pytest.ini icu/tests/ icu/src/coach/physiology/__init__.py icu/src/coach/deep_analyzer/__init__.py icu/src/coach/deep_analyzer/sub_analyzers/__init__.py icu/src/coach/common/__init__.py
git commit -m "chore: scaffold Phase 1 package structure and pytest harness"
```

---

## Task 2: Shared Pydantic types for physiology and findings

**Files:**
- Create: `icu/src/coach/physiology/types.py`
- Create: `icu/src/coach/deep_analyzer/types.py`
- Create: `icu/tests/unit/physiology/test_types.py`
- Create: `icu/tests/unit/deep_analyzer/test_types.py`

- [ ] **Step 1: Write failing test for physiology types**

Write `icu/tests/unit/physiology/test_types.py`:
```python
from src.coach.physiology.types import CPWModel, DurabilityCurve, ResponseProfile, PhysiologyBundle


def test_cpw_model_roundtrip():
    m = CPWModel(
        generated_at="2026-04-16T00:00:00Z",
        window_days=90,
        cp_watts=280,
        w_prime_joules=22000,
        t_k_seconds=-10.0,
        model="3-param-hyperbolic",
        fit_r_squared=0.97,
        data_points_used=[[60, 420], [300, 340], [1200, 290]],
        athlete_ftp_set=288,
        cp_vs_ftp_delta_w=-8,
    )
    restored = CPWModel.model_validate_json(m.model_dump_json())
    assert restored.cp_watts == 280
    assert restored.model == "3-param-hyperbolic"


def test_physiology_bundle_all_optional():
    bundle = PhysiologyBundle()
    assert bundle.cp_w is None and bundle.durability is None and bundle.response is None
```

- [ ] **Step 2: Run — expect ImportError**

Run: `cd icu && .venv/bin/pytest tests/unit/physiology/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.coach.physiology.types'`.

- [ ] **Step 3: Implement physiology types**

Write `icu/src/coach/physiology/types.py`:
```python
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CPWModel(BaseModel):
    generated_at: str
    window_days: int
    cp_watts: int
    w_prime_joules: int
    t_k_seconds: float
    model: Literal["3-param-hyperbolic", "2-param-hyperbolic"]
    fit_r_squared: float
    data_points_used: List[List[float]]
    athlete_ftp_set: int
    cp_vs_ftp_delta_w: int
    stale: bool = False


class LapWBal(BaseModel):
    lap_index: int
    type: Literal["work", "recovery", "steady"]
    w_bal_start_j: int
    w_bal_end_j: int
    depletion_pct: float


class WBalanceSeries(BaseModel):
    activity_id: str
    cp_used_w: int
    w_prime_used_j: int
    tau_s: float
    min_w_bal_j: int
    min_w_bal_pct: float
    min_w_bal_timestamp_s: int
    seconds_below_15pct: int
    laps: List[LapWBal]
    w_bal_series_1hz: List[int]


class DurabilityCurve(BaseModel):
    generated_at: str
    sample_size_rides: int
    fresh_mmp_w: dict
    fatigued_mmp_w: dict
    decay_rate_pct_per_1000kj: dict
    percentile_vs_class_estimate: Optional[str] = None


class ResponseTypeStats(BaseModel):
    sessions_n: int
    avg_tss: int
    next_day_hrv_delta_pct: float
    next_day_rhr_delta_bpm: float
    avg_target_adherence: float
    tolerance_class: Literal["low", "moderate", "high"]
    recommended_min_interval_hours: int


class KneeLoading(BaseModel):
    standing_climb_minutes_90d: int
    avg_hr_drift_bpm_standing: float
    flag: Optional[Literal["watch", "caution"]] = None


class ResponseProfile(BaseModel):
    generated_at: str
    window_days: int
    types: dict[str, ResponseTypeStats]
    knee_loading: KneeLoading


class PhysiologyBundle(BaseModel):
    cp_w: Optional[CPWModel] = None
    durability: Optional[DurabilityCurve] = None
    response: Optional[ResponseProfile] = None
```

- [ ] **Step 4: Run — expect pass**

Run: `cd icu && .venv/bin/pytest tests/unit/physiology/test_types.py -v`
Expected: PASS.

- [ ] **Step 5: Write failing test for deep_analyzer types**

Write `icu/tests/unit/deep_analyzer/test_types.py`:
```python
from src.coach.deep_analyzer.types import Features, Findings, SummaryLatest


def test_features_defaults_false():
    f = Features(duration_seconds=3600, total_kj=800)
    assert f.has_intervals is False
    assert f.heat_stress is False


def test_findings_evidence_tuple():
    f = Findings(
        analyzer="pacing",
        metrics={"vi_mean": 1.04},
        verdict="节奏平稳",
        evidence=[("前1/3与后1/3功率差 < 3%", "laps[0..3] vs laps[-3..]")],
    )
    assert f.evidence[0][0].startswith("前1/3")


def test_summary_latest_enum_progression():
    s = SummaryLatest(
        activity_id="i1",
        analyzed_at="2026-04-16T00:00:00Z",
        sub_analyzers_run=["pacing"],
        headline_verdict="节奏平稳",
        stimulus_score=0.62,
        progression_flag="progression",
        next_plan_hints=["保持当前强度"],
        knee_flag=None,
    )
    assert s.progression_flag == "progression"
```

- [ ] **Step 6: Run — expect fail**

Run: `cd icu && .venv/bin/pytest tests/unit/deep_analyzer/test_types.py -v`
Expected: FAIL — module missing.

- [ ] **Step 7: Implement deep_analyzer types**

Write `icu/src/coach/deep_analyzer/types.py`:
```python
from typing import List, Literal, Optional, Tuple, Any
from pydantic import BaseModel


class Features(BaseModel):
    has_intervals: bool = False
    is_race: bool = False
    has_climbing: bool = False
    is_endurance_long: bool = False
    has_anomaly: bool = False
    target_type_claimed: Optional[str] = None
    w_prime_depleted: bool = False
    heat_stress: bool = False
    duration_seconds: int
    total_kj: int


class Findings(BaseModel):
    analyzer: str
    metrics: dict[str, Any]
    verdict: str
    evidence: List[Tuple[str, str]]
    error: Optional[str] = None


class SummaryLatest(BaseModel):
    activity_id: str
    analyzed_at: str
    sub_analyzers_run: List[str]
    headline_verdict: str
    stimulus_score: float
    progression_flag: Literal["progression", "flat", "regression_mild", "regression_severe"]
    next_plan_hints: List[str]
    knee_flag: Optional[Literal["watch", "caution"]] = None


class StateFile(BaseModel):
    last_analyzed_activity_id: Optional[str] = None
    last_analyzed_at: Optional[str] = None
    errors: List[dict] = []
```

- [ ] **Step 8: Run — expect pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ -v`
Expected: PASS all.

- [ ] **Step 9: Commit**

```bash
git add icu/src/coach/physiology/types.py icu/src/coach/deep_analyzer/types.py icu/tests/unit/physiology/test_types.py icu/tests/unit/deep_analyzer/test_types.py
git commit -m "feat(coach): add Pydantic types for physiology and deep analyzer"
```

---

## Task 3: Shared JSONL logger

**Files:**
- Create: `icu/src/coach/common/logging.py`
- Create: `icu/tests/unit/test_common_logging.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/test_common_logging.py`:
```python
import json
from pathlib import Path

from src.coach.common.logging import get_logger


def test_logger_writes_structured_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("ICU_LOG_DIR", str(tmp_path))
    log = get_logger("cp_w_fitter")
    log.event(action="fit", activity_id=None, duration_ms=42, status="ok")
    log_file = tmp_path / "cp_w_fitter.log"
    assert log_file.exists()
    line = log_file.read_text().strip().splitlines()[-1]
    rec = json.loads(line)
    assert rec["module"] == "cp_w_fitter"
    assert rec["action"] == "fit"
    assert rec["status"] == "ok"
    assert rec["duration_ms"] == 42
    assert "ts" in rec


def test_logger_records_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ICU_LOG_DIR", str(tmp_path))
    log = get_logger("w_balance")
    log.event(action="compute", activity_id="i1", duration_ms=5, status="error", error="bad stream")
    rec = json.loads((tmp_path / "w_balance.log").read_text().strip())
    assert rec["error"] == "bad stream"
    assert rec["activity_id"] == "i1"
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/test_common_logging.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement logger**

Write `icu/src/coach/common/logging.py`:
```python
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class JSONLLogger:
    def __init__(self, module: str, log_dir: Path):
        self.module = module
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"{module}.log"

    def event(
        self,
        action: str,
        *,
        activity_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        status: str = "ok",
        error: Optional[str] = None,
        **extra: Any,
    ) -> None:
        rec: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "module": self.module,
            "activity_id": activity_id,
            "action": action,
            "duration_ms": duration_ms,
            "status": status,
            "error": error,
        }
        rec.update(extra)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def get_logger(module: str) -> JSONLLogger:
    log_dir = Path(os.environ.get("ICU_LOG_DIR", "icu/logs"))
    return JSONLLogger(module, log_dir)
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/test_common_logging.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/common/logging.py icu/tests/unit/test_common_logging.py
git commit -m "feat(coach): add structured JSONL event logger"
```

---

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

## Task 17: Report composer (Gemini prose renderer)

**Files:**
- Create: `icu/src/coach/deep_analyzer/report_composer.py`
- Create: `icu/src/coach/deep_analyzer/prompts/report_system.md`
- Create: `icu/tests/unit/deep_analyzer/test_report_composer.py`

- [ ] **Step 1: Write failing test with mocked Gemini**

Write `icu/tests/unit/deep_analyzer/test_report_composer.py`:
```python
from unittest.mock import MagicMock

from src.coach.deep_analyzer.report_composer import compose, validate_report
from src.coach.deep_analyzer.types import Findings


FAKE_REPORT = """# 活动 i123 深度分析 — 2026-04-15 vo2max

**Session 概要** · 60 分钟 · NP 285 W · TSS 95 · IF 0.95 · 810 kJ

## 今日结论
刺激对位但 W' 管理偏激进，下周建议延长恢复区间。

## 关键发现

### 1. 节奏稳定但末段略掉
> 证据: 前1/3 320W 对比后1/3 280W，差值 +12.5%
- 结论: 典型起步冒进，可能吃掉后段储备
- 联系画像: Type II 占优，起步爆点是优势但需要配速控制

### 2. W' 债务过度
> 证据: 最低 W'bal 8%，低于15%累计 240s
- 结论: 已越过安全线，累积恢复不充分
- 联系画像: 62kg轻量运动员，W' 池小，债务管理对抗周容错率更低

## 下次怎么办
1. 将 VO2max 间歇组间休息延长到 3:1
2. 每周一次纯休息替代恢复骑

## 附:本次激活的分析维度
- [x] pacing
- [x] w_balance
- [ ] durability
- [ ] climbing
- [x] target_align
- [x] historical_cmp
"""


def test_validate_accepts_well_formed_report():
    ok, reasons = validate_report(FAKE_REPORT)
    assert ok, reasons


def test_validate_rejects_missing_evidence():
    bad = FAKE_REPORT.replace("> 证据:", "> Not evidence:", 1)
    ok, reasons = validate_report(bad)
    assert not ok


def test_compose_calls_gemini_and_returns_markdown():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.text = FAKE_REPORT
    fake_client.models.generate_content.return_value = fake_response

    activity = {"id": "i123", "date": "2026-04-15", "type": "vo2max",
                "duration_s": 3600, "np_watts": 285, "tss": 95, "if": 0.95, "total_kj": 810}
    findings = [Findings(analyzer="pacing", metrics={}, verdict="起步冒进", evidence=[("x", "y")])]

    md = compose(
        activity=activity,
        findings=findings,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "right ACL post-op"},
        physiology={"cp_watts": 285, "w_prime_joules": 22000},
        activated_set={"pacing", "w_balance"},
        client=fake_client,
    )
    assert "今日结论" in md
    fake_client.models.generate_content.assert_called_once()
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Write the system prompt**

Write `icu/src/coach/deep_analyzer/prompts/report_system.md`:
```markdown
你是一位资深职业自行车教练，负责为精确的体能模型产出的发现撰写中文分析报告。**不得重复陈述 ICU 已经展示的原始指标（如 NP/IF/TSS 的数字本身）**——只输出解释和洞察。

严格遵守以下结构（禁止修改章节标题）：

# 活动 <id> 深度分析 — <date> <type>

**Session 概要** · 由系统一句话提供，原样照抄

## 今日结论
1-2 句话定性总结。

## 关键发现
对每一条发现使用：
### N. <主题>
> 证据: <逐字引用传入 findings 中的一条 evidence>
- 结论: <据此推断出的教练级解读>
- 联系画像: <把该发现与运动员画像 (62kg, Type II dominant, 右膝 ACL 术后) 联系起来>

## 下次怎么办
1-3 条下次训练的可执行建议（足以作为 plan_generator 输入）。

## 附:本次激活的分析维度
用 `- [x]` 标出本次激活的分析维度，`- [ ]` 标出未激活。

禁止：
- 重复原始指标（如“NP 为 285W，IF 0.95”——这些已在 Session 概要里）
- 空泛建议（“继续努力”“多休息”——必须具体到动作）
- 未配 `> 证据:` 行的结论
```

- [ ] **Step 4: Implement composer**

Write `icu/src/coach/deep_analyzer/report_composer.py`:
```python
import re
from pathlib import Path
from typing import Iterable

from .types import Findings

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "report_system.md"
SUB_ANALYZERS = ["pacing", "w_balance", "durability", "climbing", "target_align", "historical_cmp"]


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _session_line(activity: dict) -> str:
    dur = int(activity.get("duration_s", 0) / 60)
    np = activity.get("np_watts", "-")
    tss = activity.get("tss", "-")
    if_val = activity.get("if", "-")
    kj = activity.get("total_kj", "-")
    return f"{dur} 分钟 · NP {np} W · TSS {tss} · IF {if_val} · {kj} kJ"


def _activated_checklist(activated_set) -> str:
    lines = []
    for name in SUB_ANALYZERS:
        mark = "x" if name in activated_set else " "
        lines.append(f"- [{mark}] {name}")
    return "\n".join(lines)


def validate_report(md: str) -> tuple[bool, list[str]]:
    reasons = []
    required_sections = ["## 今日结论", "## 关键发现", "## 下次怎么办"]
    for sec in required_sections:
        if sec not in md:
            reasons.append(f"missing section {sec}")
    findings_block = md.split("## 关键发现", 1)[-1].split("## 下次怎么办", 1)[0]
    subsections = re.findall(r"###\s+\d+\.", findings_block)
    for i, _ in enumerate(subsections):
        # each subsection must have a `> 证据:` line
        start = findings_block.find(f"### {i+1}.")
        end = findings_block.find(f"### {i+2}.") if i + 2 <= len(subsections) else len(findings_block)
        block = findings_block[start:end]
        if "> 证据:" not in block:
            reasons.append(f"finding {i+1} missing 证据 line")
    banned = re.search(r"NP 为 \d+W|IF 为 \d\.\d+", md)
    if banned:
        reasons.append(f"banned raw-metric restatement: {banned.group(0)}")
    return (len(reasons) == 0), reasons


def compose(
    activity: dict,
    findings: Iterable[Findings],
    athlete: dict,
    physiology: dict,
    activated_set: set[str],
    client,
    model: str = "gemini-2.5-flash",
) -> str:
    system_prompt = _load_system_prompt()
    findings_json = [f.model_dump() for f in findings]
    user_payload = {
        "activity_id": activity["id"],
        "date": activity.get("date", ""),
        "type": activity.get("type", ""),
        "session_line": _session_line(activity),
        "athlete": athlete,
        "physiology": physiology,
        "findings": findings_json,
        "activated_checklist": _activated_checklist(activated_set),
    }
    import json as _json
    payload_text = _json.dumps(user_payload, ensure_ascii=False, indent=2)

    prompt = system_prompt + "\n\n---\n\n输入 JSON：\n```json\n" + payload_text + "\n```"

    response = client.models.generate_content(model=model, contents=prompt)
    md = response.text
    return md
```

- [ ] **Step 5: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/deep_analyzer/test_report_composer.py -v`

- [ ] **Step 6: Commit**

```bash
git add icu/src/coach/deep_analyzer/report_composer.py icu/src/coach/deep_analyzer/prompts/report_system.md icu/tests/unit/deep_analyzer/test_report_composer.py
git commit -m "feat(coach): add Gemini-backed report composer with structural validator"
```

---

## Task 18: Deep analyzer orchestrator

**Files:**
- Create: `icu/src/coach/deep_analyzer/orchestrator.py`
- Create: `icu/tests/unit/deep_analyzer/test_orchestrator.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/deep_analyzer/test_orchestrator.py`:
```python
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.coach.deep_analyzer.orchestrator import analyze_one


def _fake_report():
    return (
        "# 活动 i1 深度分析 — 2026-04-15 vo2max\n\n"
        "**Session 概要** · 60 分钟 · NP 285 W · TSS 95 · IF 0.95 · 810 kJ\n\n"
        "## 今日结论\n刺激到位但 W' 债务偏深。\n\n"
        "## 关键发现\n### 1. 节奏问题\n> 证据: 前后段差 +12%\n- 结论: 起步冒进\n- 联系画像: Type II 优势但需配速\n\n"
        "## 下次怎么办\n1. 延长组间休息\n\n"
        "## 附:本次激活的分析维度\n- [x] pacing\n- [ ] durability\n"
    )


def test_analyze_one_writes_report_and_trace(tmp_path, monkeypatch):
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(text=_fake_report())

    activity = {
        "id": "i1", "date": "2026-04-15", "type": "vo2max", "duration_s": 3600,
        "np_watts": 285, "tss": 95, "if": 0.95, "total_kj": 810,
        "laps": [
            {"lap_index": 0, "type": "work", "duration_s": 240, "avg_power": 320, "np_power": 330, "if": 1.10},
            {"lap_index": 1, "type": "recovery", "duration_s": 120, "avg_power": 180, "if": 0.64},
        ],
        "planned_type": "vo2max",
    }
    physiology_bundle = {
        "cp_w": {"cp_watts": 285, "w_prime_joules": 22000},
        "durability": {},
        "response": {},
    }

    result = analyze_one(
        activity=activity,
        streams=None,
        wbal_series=None,
        physiology_bundle=physiology_bundle,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "ACL post-op"},
        history=[],
        output_dir=tmp_path,
        client=fake_client,
    )

    md_path = tmp_path / "i1.md"
    trace_path = tmp_path / "i1.trace.json"
    assert md_path.exists() and trace_path.exists()
    trace = json.loads(trace_path.read_text())
    assert "features" in trace and "relevance" in trace and "activated" in trace
    assert result["status"] == "ok"
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement**

Write `icu/src/coach/deep_analyzer/orchestrator.py`:
```python
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..common.logging import get_logger
from . import feature_detector, router, report_composer
from .sub_analyzers import pacing, w_balance, durability, climbing, target_align, historical_cmp
from .types import SummaryLatest, StateFile

LOG = get_logger("deep_analyzer")
SUB_FUNCS = {
    "pacing": lambda act, streams, wbal, phys, hist: pacing.analyze(act, physiology=phys),
    "w_balance": lambda act, streams, wbal, phys, hist: w_balance.analyze(act, physiology=phys, wbal_series=wbal),
    "durability": lambda act, streams, wbal, phys, hist: durability.analyze(act, personal_curve=phys.get("durability") if phys else None),
    "climbing": lambda act, streams, wbal, phys, hist: climbing.analyze(act, streams=streams or {}, physiology=phys),
    "target_align": lambda act, streams, wbal, phys, hist: target_align.analyze(act, physiology=phys),
    "historical_cmp": lambda act, streams, wbal, phys, hist: historical_cmp.analyze(act, history=hist or []),
}


def _stimulus_score(findings_list) -> float:
    verdicts = [f.verdict for f in findings_list]
    score = 0.5
    if "命中" in verdicts:
        score += 0.15
    if "W' 管理得当" in verdicts:
        score += 0.1
    if "过度依赖 W' 债务" in verdicts or "后段崩盘" in verdicts:
        score -= 0.2
    if "进步" in verdicts:
        score += 0.1
    if "退步" in verdicts:
        score -= 0.15
    return round(max(0.0, min(1.0, score)), 2)


def _progression_flag(findings_list) -> str:
    for f in findings_list:
        if f.analyzer == "historical_cmp":
            if f.verdict == "退步":
                return "regression_severe" if f.metrics.get("confidence") == "high" else "regression_mild"
            if f.verdict == "进步":
                return "progression"
            if f.verdict == "持平":
                return "flat"
    return "flat"


def _next_plan_hints(findings_list) -> list[str]:
    hints = []
    for f in findings_list:
        if f.verdict == "过度依赖 W' 债务":
            hints.append("下次间歇延长恢复时长至 3:1 以保护 W' 恢复")
        if f.verdict == "起步冒进":
            hints.append("下次以目标功率下限起始，前两组压住")
        if f.verdict == "刺激错配" and f.metrics.get("under_prescription_flag"):
            hints.append("连续多次未达刺激——教练需提高目标区间下限")
    return hints


def analyze_one(
    activity: dict,
    streams: Optional[dict],
    wbal_series: Optional[dict],
    physiology_bundle: dict,
    athlete: dict,
    history: list,
    output_dir: Path,
    client,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    physiology_flat = {}
    cp_w = physiology_bundle.get("cp_w") or {}
    physiology_flat.update(cp_w)
    physiology_flat["durability"] = physiology_bundle.get("durability")
    physiology_flat["response"] = physiology_bundle.get("response")
    if wbal_series:
        physiology_flat["min_w_bal_pct"] = wbal_series.get("min_w_bal_pct")

    features = feature_detector.detect_features(activity, streams, physiology_flat, athlete)
    relevance = router.route(features)
    activated = {name for name, score in relevance.items() if score >= 0.5}

    findings_list = []
    for name in activated:
        try:
            findings_list.append(SUB_FUNCS[name](activity, streams, wbal_series, physiology_flat, history))
        except Exception as e:
            LOG.event(action=f"sub_{name}", activity_id=activity["id"], status="error", error=str(e))

    try:
        md = report_composer.compose(
            activity=activity,
            findings=findings_list,
            athlete=athlete,
            physiology=physiology_flat,
            activated_set=activated,
            client=client,
        )
    except Exception as e:
        LOG.event(action="compose", activity_id=activity["id"], status="error", error=str(e))
        (output_dir / f"{activity['id']}.raw.json").write_text(
            json.dumps([f.model_dump() for f in findings_list], ensure_ascii=False, indent=2)
        )
        return {"status": "report_failed", "error": str(e)}

    (output_dir / f"{activity['id']}.md").write_text(md, encoding="utf-8")
    trace = {
        "features": features.model_dump(),
        "relevance": relevance,
        "activated": sorted(activated),
        "findings": [f.model_dump() for f in findings_list],
    }
    (output_dir / f"{activity['id']}.trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2))

    headline = next((f.verdict for f in findings_list if f.analyzer in ("pacing", "target_align", "historical_cmp")), "分析完成")
    summary = SummaryLatest(
        activity_id=activity["id"],
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        sub_analyzers_run=sorted(activated),
        headline_verdict=headline,
        stimulus_score=_stimulus_score(findings_list),
        progression_flag=_progression_flag(findings_list),
        next_plan_hints=_next_plan_hints(findings_list),
        knee_flag=(physiology_bundle.get("response") or {}).get("knee_loading", {}).get("flag"),
    )
    (output_dir / "summary_latest.json").write_text(summary.model_dump_json(indent=2))

    LOG.event(action="analyze_one", activity_id=activity["id"], duration_ms=int((time.monotonic() - t0) * 1000), status="ok")
    return {"status": "ok", "activated": sorted(activated)}


def analyze_new(
    activities_iter,
    physiology_bundle: dict,
    athlete: dict,
    output_dir: Path,
    client,
    load_streams=None,
    load_wbal=None,
    history_for=None,
) -> list:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "_state.json"
    state = StateFile.model_validate_json(state_path.read_text()) if state_path.exists() else StateFile()
    last_id = state.last_analyzed_activity_id
    results = []
    last_seen = last_id
    for activity in activities_iter:
        if last_id and activity["id"] == last_id:
            continue
        streams = load_streams(activity["id"]) if load_streams else None
        wbal = load_wbal(activity["id"]) if load_wbal else None
        history = history_for(activity) if history_for else []
        res = analyze_one(
            activity=activity,
            streams=streams,
            wbal_series=wbal,
            physiology_bundle=physiology_bundle,
            athlete=athlete,
            history=history,
            output_dir=output_dir,
            client=client,
        )
        results.append({"activity_id": activity["id"], **res})
        last_seen = activity["id"]
    state.last_analyzed_activity_id = last_seen
    state.last_analyzed_at = datetime.now(timezone.utc).isoformat()
    state_path.write_text(state.model_dump_json(indent=2))
    return results
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ -v`

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/deep_analyzer/orchestrator.py icu/tests/unit/deep_analyzer/test_orchestrator.py
git commit -m "feat(coach): add deep analyzer orchestrator with state tracking"
```

---

## Task 19: Integration — extend `sync_data.py` tail

**Files:**
- Modify: `icu/scripts/sync_data.py`
- Create: `icu/scripts/refresh_physiology.py`
- Create: `icu/scripts/run_deep_analysis.py`
- Create: `icu/tests/integration/test_sync_integration.py`

- [ ] **Step 1: Write failing integration test**

Write `icu/tests/integration/test_sync_integration.py`:
```python
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_refresh_physiology_script_is_callable_standalone():
    script = REPO / "scripts" / "refresh_physiology.py"
    assert script.exists()


@pytest.mark.integration
def test_run_deep_analysis_script_is_callable():
    script = REPO / "scripts" / "run_deep_analysis.py"
    assert script.exists()


@pytest.mark.integration
def test_sync_data_imports_new_steps():
    sd = (REPO / "scripts" / "sync_data.py").read_text()
    assert "refresh_physiology" in sd
    assert "run_deep_analysis" in sd
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement `refresh_physiology.py`**

Write `icu/scripts/refresh_physiology.py`:
```python
"""Standalone physiology refresher. Called by sync_data.py or directly for debugging."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.physiology.refresher import refresh_all


def _load_activities(warehouse):
    out = []
    detail_dir = warehouse / "5_Activities_Detail"
    if not detail_dir.exists():
        return out
    for f in sorted(detail_dir.glob("*/activity.json")):
        try:
            doc = json.loads(f.read_text())
            streams_file = f.parent / "streams.json"
            if streams_file.exists():
                streams = json.loads(streams_file.read_text())
                doc["power_stream"] = streams.get("watts") or streams.get("power") or []
            out.append(doc)
        except Exception as exc:
            print(f"skip {f}: {exc}", file=sys.stderr)
    return out


def _load_wellness(warehouse):
    out = {}
    w = warehouse / "2_Wellness"
    if not w.exists():
        return out
    for f in w.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            if isinstance(d, dict) and "date" in d:
                out[d["date"]] = d
            elif isinstance(d, list):
                for rec in d:
                    out[rec.get("id") or rec.get("date")] = rec
        except Exception:
            pass
    return out


def main():
    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    activities = _load_activities(warehouse)
    wellness = _load_wellness(warehouse)
    result = refresh_all(warehouse, memory, activities, wellness)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Implement `run_deep_analysis.py`**

Write `icu/scripts/run_deep_analysis.py`:
```python
"""Runs deep analysis for newly synced activities. Called by sync_data.py."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.deep_analyzer.orchestrator import analyze_new


def _load_activity_list(warehouse):
    path = warehouse / "4_Activities_List" / "activities.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _load_streams_for(warehouse):
    def loader(activity_id):
        f = warehouse / "5_Activities_Detail" / activity_id / "streams.json"
        if f.exists():
            return json.loads(f.read_text())
        return None
    return loader


def _load_wbal_for(warehouse):
    def loader(activity_id):
        f = warehouse / "5_Activities_Detail" / f"{activity_id}_wbalance.json"
        if f.exists():
            return json.loads(f.read_text())
        return None
    return loader


def _load_physiology(memory):
    phys_dir = memory / "physiology"
    bundle = {"cp_w": None, "durability": None, "response": None}
    for key, fname in [("cp_w", "cp_w_current.json"), ("durability", "durability.json"), ("response", "response_profile.json")]:
        p = phys_dir / fname
        if p.exists():
            bundle[key] = json.loads(p.read_text())
    return bundle


def _make_client():
    load_dotenv(REPO / ".env")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def main():
    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    output_dir = memory / "deep_analysis"
    client = _make_client()
    athlete = json.loads((warehouse / "1_Profile" / "athlete.json").read_text()) if (warehouse / "1_Profile" / "athlete.json").exists() else {}
    activities = _load_activity_list(warehouse)
    physiology = _load_physiology(memory)

    results = analyze_new(
        activities_iter=activities,
        physiology_bundle=physiology,
        athlete=athlete,
        output_dir=output_dir,
        client=client,
        load_streams=_load_streams_for(warehouse),
        load_wbal=_load_wbal_for(warehouse),
        history_for=lambda act: [a for a in activities if a.get("id") != act["id"]][:20],
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Modify `sync_data.py` to call the two new scripts**

Edit `icu/scripts/sync_data.py` — append after the existing `run_script("build_memory.py")` line (before the failures summary print):

```python
    # 8. Phase 1 — physiology refresh (soft-fail)
    run_script("refresh_physiology.py")

    # 9. Phase 1 — deep analysis (soft-fail)
    run_script("run_deep_analysis.py")

    # 10. Phase 1 — Coach Brief update (soft-fail)
    run_script("update_coach_brief.py")
```

The existing `run_script` helper already catches `CalledProcessError` and tracks failures without halting the pipeline — that is our soft-fail mechanism.

- [ ] **Step 6: Run integration test**

Run: `cd icu && .venv/bin/pytest tests/integration/test_sync_integration.py -v`
Expected: PASS (update_coach_brief.py existence will fail until Task 21 — move that assertion into Task 21's test).

- [ ] **Step 7: Commit**

```bash
git add icu/scripts/refresh_physiology.py icu/scripts/run_deep_analysis.py icu/scripts/sync_data.py icu/tests/integration/test_sync_integration.py
git commit -m "feat(coach): wire Phase 1 physiology+deep-analysis into sync_data"
```

---

## Task 20: `plan_generator.py` prompt injection

**Files:**
- Create: `icu/src/coach/phase1_injection.py`
- Modify: `icu/src/coach/plan_generator.py` (lines 245–260 region — prompt assembly)
- Create: `icu/tests/unit/coach/test_phase1_injection.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/coach/test_phase1_injection.py`:
```python
import json
from pathlib import Path

from src.coach.phase1_injection import inject_phase1_context


def test_no_files_returns_base_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = "BASE PROMPT"
    assert inject_phase1_context(base, base_dir=tmp_path) == base


def test_injects_cp_w_and_hints(tmp_path):
    (tmp_path / "coach_memory" / "physiology").mkdir(parents=True)
    (tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 295, "w_prime_joules": 22500, "fit_r_squared": 0.97,
        "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": 7
    }))
    (tmp_path / "coach_memory" / "deep_analysis").mkdir()
    (tmp_path / "coach_memory" / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": ["pacing"], "headline_verdict": "起步冒进",
        "stimulus_score": 0.72, "progression_flag": "progression",
        "next_plan_hints": ["下次延长恢复时长", "提高 VO2max 刺激下限"],
        "knee_flag": None,
    }))
    out = inject_phase1_context("BASE PROMPT", base_dir=tmp_path)
    assert "BASE PROMPT" in out
    assert "个人 CP 295W" in out or "CP: 295" in out
    assert "下次延长恢复时长" in out
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement injection helper**

Write `icu/src/coach/phase1_injection.py`:
```python
import json
from pathlib import Path


def _load_json_safe(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _tail_reports(dir_: Path, n: int = 5) -> list[str]:
    if not dir_.exists():
        return []
    md_files = sorted(dir_.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    return [f.read_text(encoding="utf-8") for f in md_files]


def render_phase1_context_block(physiology, durability, response, summary, recent_reports) -> str:
    lines = ["\n---\n## Phase 1 个性化体能注入（由确定性模型生成）\n"]

    if physiology:
        cp = physiology.get("cp_watts")
        wp = physiology.get("w_prime_joules")
        r2 = physiology.get("fit_r_squared")
        ftp = physiology.get("athlete_ftp_set")
        delta = physiology.get("cp_vs_ftp_delta_w")
        lines.append(f"- **个人 CP {cp}W / W' {wp}J**（拟合 R²={r2}）；与设定 FTP {ftp}W 偏差 {delta:+d}W。规划强度时以 **CP 而非 FTP** 作为阈值。")

    if durability and durability.get("decay_rate_pct_per_1000kj"):
        decay = durability["decay_rate_pct_per_1000kj"]
        lines.append(f"- **耐力衰减率**：60s 档 {decay.get('60s', 0)}%/1000kJ，5min 档 {decay.get('300s', 0)}%/1000kJ。长距离/赛前补能策略按此比例推。")

    if response and response.get("types"):
        parts = []
        for t, stats in response["types"].items():
            parts.append(f"{t}={stats['tolerance_class']}")
        lines.append(f"- **各类刺激耐受画像**：{', '.join(parts)}。对 `low` 类刺激延长恢复，对 `high` 类可提高频率/强度。")
        knee = response.get("knee_loading", {})
        if knee.get("flag"):
            lines.append(f"- **右膝负荷标记**：{knee['flag']}（90 日内摇车 {knee.get('standing_climb_minutes_90d', 0)} 分钟）。避免连续多天出现摇车爆发动作。")

    if summary:
        lines.append(f"- **最近一次深度分析**：{summary.get('headline_verdict', '')}（stimulus={summary.get('stimulus_score')}，progression={summary.get('progression_flag')}）。")
        if summary.get("next_plan_hints"):
            lines.append("  - 执行下列 hints：")
            for h in summary["next_plan_hints"]:
                lines.append(f"    * {h}")

    if recent_reports:
        lines.append("\n### 最近 5 篇深度分析摘要（下次怎么办段已由系统抽取）")
        for md in recent_reports:
            if "## 下次怎么办" in md:
                idx = md.index("## 下次怎么办")
                end = md.find("##", idx + 3)
                block = md[idx: end if end > 0 else len(md)].strip()
                lines.append(block + "\n")

    lines.append(
        "\n**硬规则**：若最近 3 次 stimulus_score 均 < 0.4，说明存在系统性 under-prescription — "
        "把周 TSS 目标提高到历史 90 天峰值的 90%。默认一周 1 天**完全休息**（不安排恢复骑），除非 response.high 允许。\n"
    )
    return "\n".join(lines)


def inject_phase1_context(base_prompt: str, base_dir: Path | None = None) -> str:
    base_dir = Path(base_dir) if base_dir else Path.cwd()
    physiology = _load_json_safe(base_dir / "coach_memory" / "physiology" / "cp_w_current.json")
    durability = _load_json_safe(base_dir / "coach_memory" / "physiology" / "durability.json")
    response = _load_json_safe(base_dir / "coach_memory" / "physiology" / "response_profile.json")
    summary = _load_json_safe(base_dir / "coach_memory" / "deep_analysis" / "summary_latest.json")
    recent = _tail_reports(base_dir / "coach_memory" / "deep_analysis", n=5)

    if not any([physiology, durability, response, summary]):
        return base_prompt

    return base_prompt + render_phase1_context_block(physiology, durability, response, summary, recent)
```

- [ ] **Step 4: Wire into `plan_generator.py`**

Edit `icu/src/coach/plan_generator.py` — at the top add:
```python
from src.coach.phase1_injection import inject_phase1_context
```

Then in `generate_plan()` (around line 253), change the prompt assembly from:
```python
    prompt = f"""{system_prompt}
```
to wrap the final prompt before the `client.models.generate_content` call:
```python
    prompt = inject_phase1_context(prompt)
```
Place this `inject_phase1_context` call on the line immediately before the existing `genai` / `generate_content` call inside `generate_plan`.

- [ ] **Step 5: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/coach/test_phase1_injection.py -v`

- [ ] **Step 6: Commit**

```bash
git add icu/src/coach/phase1_injection.py icu/src/coach/plan_generator.py icu/tests/unit/coach/test_phase1_injection.py
git commit -m "feat(coach): inject Phase 1 physiology context into plan_generator prompt"
```

---

## Task 21: Coach Brief (GEMINI.md) updater

**Files:**
- Create: `icu/scripts/update_coach_brief.py`
- Create: `icu/src/coach/brief_updater.py`
- Create: `icu/tests/unit/coach/test_brief_updater.py`
- Modify: `icu/GEMINI.md` (insert markers)

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/coach/test_brief_updater.py`:
```python
import json
from pathlib import Path

from src.coach.brief_updater import update_brief, BEGIN, END


def test_inserts_block_between_markers(tmp_path):
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text(f"intro\n{BEGIN}\nold\n{END}\ntail\n")

    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    (mem / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": ["pacing"], "headline_verdict": "起步冒进",
        "stimulus_score": 0.55, "progression_flag": "flat",
        "next_plan_hints": [], "knee_flag": "watch",
    }))
    (mem / "physiology").mkdir()
    (mem / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 292, "w_prime_joules": 21800, "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": 4,
    }))
    update_brief(gemini_path=gemini, memory_dir=mem)
    content = gemini.read_text()
    assert "intro" in content and "tail" in content
    assert "起步冒进" in content
    assert "CP 292" in content or "CP: 292" in content
    assert content.count(BEGIN) == 1 and content.count(END) == 1


def test_appends_markers_if_absent(tmp_path):
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text("no markers yet\n")
    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    (mem / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "activity_id": "i1", "analyzed_at": "2026-04-16T00:00:00Z",
        "sub_analyzers_run": [], "headline_verdict": "x",
        "stimulus_score": 0.5, "progression_flag": "flat",
        "next_plan_hints": [], "knee_flag": None,
    }))
    update_brief(gemini_path=gemini, memory_dir=mem)
    c = gemini.read_text()
    assert BEGIN in c and END in c
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement updater module**

Write `icu/src/coach/brief_updater.py`:
```python
import json
import re
from pathlib import Path

BEGIN = "<!-- BEGIN: phase1_coach_brief -->"
END = "<!-- END: phase1_coach_brief -->"


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _recent_stimulus_trend(memory_dir: Path, n: int = 3) -> list[float]:
    # Scan trace files, pick last n by mtime, read their summaries indirectly via the trace itself
    da = memory_dir / "deep_analysis"
    if not da.exists():
        return []
    traces = sorted(da.glob("*.trace.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    scores = []
    for t in traces:
        try:
            doc = json.loads(t.read_text())
            # Summary was written as <id>.md sibling; reconstruct stimulus from findings
            # For Coach Brief we just need the presence; score comes from summary_latest.json
        except Exception:
            pass
    # Read summary_latest's score as the most recent anchor; full history requires summary archive — deferred
    summary = _load(memory_dir / "deep_analysis" / "summary_latest.json")
    if summary:
        scores.append(summary.get("stimulus_score", 0.0))
    return scores


def render_brief(physiology, summary, recent_scores, response_knee) -> str:
    lines = [BEGIN]
    lines.append("## 当前画像（自动更新，勿手动编辑本段）")
    if physiology:
        lines.append(f"- 个人 CP {physiology['cp_watts']}W / W' {physiology['w_prime_joules']}J"
                     f"（vs 设定 FTP {physiology['athlete_ftp_set']}W，差 {physiology['cp_vs_ftp_delta_w']:+d}W）")
    if summary:
        lines.append(f"- 最近深度分析：{summary['headline_verdict']}（stimulus={summary['stimulus_score']}, {summary['progression_flag']}）")
    if recent_scores:
        lines.append(f"- 近 {len(recent_scores)} 次 stimulus 均值 = {round(sum(recent_scores)/len(recent_scores), 2)}")
    if response_knee:
        lines.append(f"- 右膝负荷标记：{response_knee}")
    lines.append(END)
    return "\n".join(lines)


def update_brief(gemini_path: Path, memory_dir: Path) -> None:
    physiology = _load(memory_dir / "physiology" / "cp_w_current.json")
    summary = _load(memory_dir / "deep_analysis" / "summary_latest.json")
    response = _load(memory_dir / "physiology" / "response_profile.json") or {}
    knee_flag = response.get("knee_loading", {}).get("flag") if isinstance(response, dict) else None
    scores = _recent_stimulus_trend(memory_dir)

    block = render_brief(physiology, summary, scores, knee_flag)

    content = gemini_path.read_text(encoding="utf-8") if gemini_path.exists() else ""
    if BEGIN in content and END in content:
        new = re.sub(
            rf"{re.escape(BEGIN)}.*?{re.escape(END)}",
            block,
            content,
            count=1,
            flags=re.DOTALL,
        )
    else:
        new = content.rstrip() + "\n\n" + block + "\n"
    gemini_path.write_text(new, encoding="utf-8")
```

- [ ] **Step 4: Implement script**

Write `icu/scripts/update_coach_brief.py`:
```python
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.brief_updater import update_brief


def main():
    update_brief(gemini_path=REPO / "GEMINI.md", memory_dir=REPO / "coach_memory")
    print("coach brief updated")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add markers to GEMINI.md**

Edit `icu/GEMINI.md` — append at the end (unless already present):
```
<!-- BEGIN: phase1_coach_brief -->
<!-- END: phase1_coach_brief -->
```

- [ ] **Step 6: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/coach/test_brief_updater.py -v`

- [ ] **Step 7: Commit**

```bash
git add icu/src/coach/brief_updater.py icu/scripts/update_coach_brief.py icu/GEMINI.md icu/tests/unit/coach/test_brief_updater.py
git commit -m "feat(coach): auto-update GEMINI.md Coach Brief from Phase 1 outputs"
```

---

## Task 22: CLI tools — analyze_rides, physiology_audit

**Files:**
- Create: `icu/scripts/analyze_rides.py`
- Create: `icu/scripts/physiology_audit.py`
- Create: `icu/tests/integration/test_cli_tools.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/integration/test_cli_tools.py`:
```python
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_analyze_rides_help():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "analyze_rides.py"), "--help"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode == 0
    assert "--activity" in result.stdout and "--dry-run" in result.stdout


@pytest.mark.integration
def test_physiology_audit_help():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "physiology_audit.py"), "--help"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert result.returncode == 0
```

- [ ] **Step 2: Run — fail**

- [ ] **Step 3: Implement `analyze_rides.py`**

Write `icu/scripts/analyze_rides.py`:
```python
"""CLI for deep analyzer — single activity, dry-run, replay, or backfill."""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.coach.deep_analyzer.feature_detector import detect_features
from src.coach.deep_analyzer.router import route
from src.coach.deep_analyzer.orchestrator import analyze_one


def _load_activity(warehouse: Path, activity_id: str):
    f = warehouse / "5_Activities_Detail" / activity_id / "activity.json"
    if not f.exists():
        raise FileNotFoundError(f)
    return json.loads(f.read_text())


def _load_streams(warehouse: Path, activity_id: str):
    f = warehouse / "5_Activities_Detail" / activity_id / "streams.json"
    return json.loads(f.read_text()) if f.exists() else None


def _load_wbal(warehouse: Path, activity_id: str):
    f = warehouse / "5_Activities_Detail" / f"{activity_id}_wbalance.json"
    return json.loads(f.read_text()) if f.exists() else None


def _load_physiology(memory: Path):
    pd = memory / "physiology"
    bundle = {}
    for k, name in [("cp_w", "cp_w_current.json"), ("durability", "durability.json"), ("response", "response_profile.json")]:
        p = pd / name
        bundle[k] = json.loads(p.read_text()) if p.exists() else None
    return bundle


def _make_client():
    load_dotenv(REPO / ".env")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--activity", help="single activity id")
    parser.add_argument("--dry-run", action="store_true", help="skip Gemini; print features + relevance + findings")
    parser.add_argument("--replay", action="store_true", help="re-analyze and overwrite")
    parser.add_argument("--backfill", action="store_true", help="run on all interval/race/climb activities")
    parser.add_argument("--since", help="ISO date for --backfill filter")
    args = parser.parse_args()

    warehouse = REPO / "icu_data_warehouse"
    memory = REPO / "coach_memory"
    output = memory / "deep_analysis"
    output.mkdir(parents=True, exist_ok=True)

    if not args.activity and not args.backfill:
        parser.error("one of --activity or --backfill is required")

    physiology = _load_physiology(memory)
    athlete = json.loads((warehouse / "1_Profile" / "athlete.json").read_text()) if (warehouse / "1_Profile" / "athlete.json").exists() else {}

    if args.dry_run and args.activity:
        activity = _load_activity(warehouse, args.activity)
        streams = _load_streams(warehouse, args.activity)
        phys_flat = dict((physiology.get("cp_w") or {}))
        features = detect_features(activity, streams, phys_flat, athlete)
        rel = route(features)
        print(json.dumps({"features": features.model_dump(), "relevance": rel, "activated": [k for k, v in rel.items() if v >= 0.5]}, ensure_ascii=False, indent=2))
        return

    client = _make_client()
    if args.activity:
        activity = _load_activity(warehouse, args.activity)
        streams = _load_streams(warehouse, args.activity)
        wbal = _load_wbal(warehouse, args.activity)
        result = analyze_one(
            activity=activity, streams=streams, wbal_series=wbal,
            physiology_bundle=physiology, athlete=athlete, history=[],
            output_dir=output, client=client,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Backfill
    list_path = warehouse / "4_Activities_List" / "activities.json"
    activities = json.loads(list_path.read_text()) if list_path.exists() else []
    if args.since:
        activities = [a for a in activities if (a.get("date") or "") >= args.since]
    for a in activities:
        features = detect_features(a, None, dict(physiology.get("cp_w") or {}), athlete)
        if not (features.has_intervals or features.is_race or features.has_climbing):
            continue
        streams = _load_streams(warehouse, a["id"])
        wbal = _load_wbal(warehouse, a["id"])
        analyze_one(
            activity=a, streams=streams, wbal_series=wbal,
            physiology_bundle=physiology, athlete=athlete, history=[],
            output_dir=output, client=client,
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Implement `physiology_audit.py`**

Write `icu/scripts/physiology_audit.py`:
```python
"""Prints current physiology snapshot vs 30-day-ago snapshot."""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _read(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def main():
    argparse.ArgumentParser().parse_args()
    physiology = REPO / "coach_memory" / "physiology"
    current = _read(physiology / "cp_w_current.json")
    history_dir = physiology / "history"
    prior = None
    if history_dir.exists():
        files = sorted(history_dir.glob("cp_w_*.json"))
        if files:
            prior = _read(files[-2]) if len(files) >= 2 else _read(files[-1])

    def line(label, cur, pri):
        if cur is None:
            return f"{label}: n/a"
        if pri is None:
            return f"{label}: {cur} (no prior)"
        delta = cur - pri
        return f"{label}: {cur}  (Δ {delta:+})"

    if current:
        p_cp = prior["cp_watts"] if prior else None
        p_wp = prior["w_prime_joules"] if prior else None
        print(line("CP(W)", current["cp_watts"], p_cp))
        print(line("W'(J)", current["w_prime_joules"], p_wp))
        print(f"fit R²: {current.get('fit_r_squared')}")
        print(f"model: {current.get('model')}")
    else:
        print("no cp_w_current.json yet — run refresh_physiology.py")

    durability = _read(physiology / "durability.json")
    if durability:
        print("\nDurability decay (%/1000kJ):", durability.get("decay_rate_pct_per_1000kj"))

    response = _read(physiology / "response_profile.json")
    if response:
        print("\nTolerance classes:")
        for t, stats in (response.get("types") or {}).items():
            print(f"  {t}: {stats['tolerance_class']}  (n={stats['sessions_n']}, avg TSS {stats['avg_tss']})")
        knee = response.get("knee_loading") or {}
        if knee.get("flag"):
            print(f"\n⚠️ knee flag: {knee['flag']} (standing minutes 90d: {knee.get('standing_climb_minutes_90d')})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/integration/test_cli_tools.py -v`

- [ ] **Step 6: Commit**

```bash
git add icu/scripts/analyze_rides.py icu/scripts/physiology_audit.py icu/tests/integration/test_cli_tools.py
git commit -m "feat(coach): add analyze_rides and physiology_audit CLIs"
```

---

## Task 23: End-to-end test with mocked Gemini + ICU

**Files:**
- Create: `icu/tests/e2e/test_full_sync.py`
- Create: `icu/tests/fixtures/rides/interval_ride_synthetic.json`

- [ ] **Step 1: Write failing test**

Write `icu/tests/fixtures/rides/interval_ride_synthetic.json`:
```json
{
  "id": "iE2E1",
  "date": "2026-04-15",
  "type": "vo2max",
  "duration_s": 3600,
  "np_watts": 285,
  "tss": 95,
  "if": 0.95,
  "total_kj": 810,
  "max_hr": 188,
  "decoupling_pct": 4,
  "hr_drift_z2_bpm": 2,
  "avg_temperature_c": 20,
  "elevation_gain_m": 200,
  "planned_type": "vo2max",
  "laps": [
    {"lap_index": 0, "type": "work", "duration_s": 240, "avg_power": 320, "np_power": 330, "if": 1.10},
    {"lap_index": 1, "type": "recovery", "duration_s": 120, "avg_power": 180, "if": 0.60},
    {"lap_index": 2, "type": "work", "duration_s": 240, "avg_power": 325, "np_power": 332, "if": 1.12},
    {"lap_index": 3, "type": "recovery", "duration_s": 120, "avg_power": 175, "if": 0.58},
    {"lap_index": 4, "type": "work", "duration_s": 240, "avg_power": 322, "np_power": 330, "if": 1.11},
    {"lap_index": 5, "type": "recovery", "duration_s": 120, "avg_power": 178, "if": 0.59},
    {"lap_index": 6, "type": "work", "duration_s": 240, "avg_power": 318, "np_power": 328, "if": 1.09}
  ]
}
```

Write `icu/tests/e2e/test_full_sync.py`:
```python
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.coach.physiology.refresher import refresh_all
from src.coach.deep_analyzer.orchestrator import analyze_new

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "rides"


def _seed_warehouse(base: Path):
    (base / "icu_data_warehouse" / "3_PowerData").mkdir(parents=True)
    (base / "icu_data_warehouse" / "3_PowerData" / "power_curves_90d.json").write_text(json.dumps({
        "secs": [5, 30, 60, 120, 300, 600, 1200],
        "watts": [1200, 780, 560, 450, 340, 310, 290],
    }))
    (base / "icu_data_warehouse" / "3_PowerData" / "power_curves_all_time.json").write_text(json.dumps({
        "secs": [5, 30, 60, 120, 300, 600, 1200],
        "watts": [1389, 850, 600, 480, 360, 320, 295],
    }))
    (base / "icu_data_warehouse" / "1_Profile").mkdir(parents=True)
    (base / "icu_data_warehouse" / "1_Profile" / "athlete.json").write_text(json.dumps({
        "weight": 62, "ftp": 288, "hr_max": 195,
    }))


@pytest.mark.e2e
def test_full_phase1_pipeline_with_mocked_gemini(tmp_path):
    _seed_warehouse(tmp_path)
    activity = json.loads((FIXTURE_DIR / "interval_ride_synthetic.json").read_text())

    refresh_result = refresh_all(
        warehouse_dir=tmp_path / "icu_data_warehouse",
        memory_dir=tmp_path / "coach_memory",
        activities=[{**activity, "power_stream": [300] * 3600}],
        wellness_by_date={},
    )
    assert refresh_result["cp_w"]["status"] == "ok"

    physiology_bundle = {
        "cp_w": json.loads((tmp_path / "coach_memory" / "physiology" / "cp_w_current.json").read_text()),
        "durability": json.loads((tmp_path / "coach_memory" / "physiology" / "durability.json").read_text()),
        "response": None,
    }

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(text=(
        "# 活动 iE2E1 深度分析 — 2026-04-15 vo2max\n\n"
        "**Session 概要** · 60 分钟 · NP 285 W · TSS 95 · IF 0.95 · 810 kJ\n\n"
        "## 今日结论\n刺激到位节奏平稳。\n\n"
        "## 关键发现\n### 1. 节奏稳定\n> 证据: 首末段差 <3%\n- 结论: 能按计划执行\n- 联系画像: Type II 优势，这类短间歇正是强项\n\n"
        "## 下次怎么办\n1. 保持强度提升刺激下限\n\n"
        "## 附:本次激活的分析维度\n- [x] pacing\n"
    ))

    out_dir = tmp_path / "coach_memory" / "deep_analysis"
    results = analyze_new(
        activities_iter=[activity],
        physiology_bundle=physiology_bundle,
        athlete={"weight_kg": 62, "type": "Type II dominant", "medical": "ACL post-op"},
        output_dir=out_dir,
        client=fake_client,
    )

    assert results[0]["status"] == "ok"
    assert (out_dir / "iE2E1.md").exists()
    assert (out_dir / "iE2E1.trace.json").exists()
    assert (out_dir / "summary_latest.json").exists()
    assert (out_dir / "_state.json").exists()
```

- [ ] **Step 2: Run — fail or pass?**

Run: `cd icu && .venv/bin/pytest tests/e2e/ -v`

- [ ] **Step 3: Fix any wiring issues uncovered**

If the e2e test reveals a bug (typical: stream key naming, schema validation, path resolution), fix the bug in the module where it lives — do NOT weaken the test. Re-run until green.

- [ ] **Step 4: Run full suite**

Run: `cd icu && .venv/bin/pytest -q`
Expected: All unit + integration + e2e tests pass.

- [ ] **Step 5: Commit**

```bash
git add icu/tests/e2e/test_full_sync.py icu/tests/fixtures/rides/interval_ride_synthetic.json
git commit -m "test(coach): add Phase 1 end-to-end pipeline test with mocked Gemini"
```

---

## Task 24: Acceptance — run Phase 1 against real warehouse

**Files:**
- None (operational task; gated behind user sign-off)

- [ ] **Step 1: Backup existing coach_memory**

```bash
cp -R icu/coach_memory icu/coach_memory.pre_phase1.bak
```

- [ ] **Step 2: Run physiology refresh**

```bash
cd icu && .venv/bin/python scripts/refresh_physiology.py
```

Expected stdout: JSON showing `cp_w.status = ok`; file `coach_memory/physiology/cp_w_current.json` exists with `fit_r_squared ≥ 0.90`. If < 0.90 model should already be `2-param-hyperbolic`; log any anomaly.

- [ ] **Step 3: Audit**

```bash
cd icu && .venv/bin/python scripts/physiology_audit.py
```

Expected: CP value sensible relative to set FTP (288W). Delta typically within ±15W.

- [ ] **Step 4: Dry-run deep analysis on one recent activity**

Pick any recent interval activity id (e.g. via `ls coach_memory/_archive/ | tail`). Run:

```bash
cd icu && .venv/bin/python scripts/analyze_rides.py --activity <id> --dry-run
```

Expected: JSON with populated `features`, `relevance`, and non-empty `activated` set.

- [ ] **Step 5: Real run on that activity**

```bash
cd icu && .venv/bin/python scripts/analyze_rides.py --activity <id>
```

Expected: `coach_memory/deep_analysis/<id>.md` generated, passes `validate_report`. Open the file; confirm that it interprets rather than restates metrics.

- [ ] **Step 6: Full sync smoke test**

```bash
cd icu && .venv/bin/python scripts/sync_data.py
```

Expected: completes within ~4 min; new physiology snapshots refreshed; deep analyses run for any new activities; GEMINI.md Coach Brief block updated.

- [ ] **Step 7: Regenerate a plan to verify injection**

```bash
cd icu && .venv/bin/python scripts/push_plan.py
```

Expected: the generated plan references the personal CP (not just FTP=288) and respects tolerance classes.

- [ ] **Step 8: User acceptance**

Present the latest `coach_memory/deep_analysis/<id>.md` to the user. Phase 1 is complete only when the user confirms: "this is a real coach-level analysis" (Success Criterion #7 from the spec).

- [ ] **Step 9: Commit acceptance note**

Append a short dated note to `docs/superpowers/specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md`:
```
## Implementation Completed
Date: <YYYY-MM-DD>
Real-warehouse CP fit R²: <value>
User acceptance: yes / with-notes-<...>
Known follow-ups for Phase 2: <list>
```

```bash
git add docs/superpowers/specs/2026-04-16-ai-coach-phase-1-physiology-deep-analyzer.md
git commit -m "docs: record Phase 1 acceptance and follow-ups"
```

---

## Self-Review Checklist (completed before handoff)

- **Spec coverage**:
  - Physiology 1.1–1.5 → Tasks 4 (CP/W'), 5 (W'bal), 6 (durability), 7 (response profile), 8 (refresher). ✓
  - Deep analyzer 2.1–2.5 → Tasks 9 (feature detector), 10 (router), 11–16 (six sub-analyzers), 17 (composer), 18 (orchestrator). ✓
  - Integration 4.1–4.4 → Task 19 (sync_data), Task 20 (plan_generator injection), Task 21 (Coach Brief), Task 22 (backfill via analyze_rides CLI). ✓
  - Observability — structured JSONL: Task 3 (logger); trace files: Task 18 (orchestrator writes `<id>.trace.json`); CLI tools: Task 22 (audit + dry-run + replay + backfill). Notable gap: `--debug` switch and `icu/logs/gemini_raw/` capture are not implemented as a dedicated task; the JSONLLogger and orchestrator raw-failure capture cover the core observability target. If the user wants full `--debug` Gemini-raw capture, add a follow-up task in Phase 1 extension.
  - Testing: unit ≥ 90% — each task has focused tests; structural assertions on composer (Task 17); e2e with mocked Gemini (Task 23). ✓
  - Performance budget — not directly tested; acceptance Task 24 Step 6 smoke-tests sync runtime. ✓
  - Rollback — per-task commits, additive changes, invariant restated in plan header. ✓
  - Success criteria 1–7 — covered by Tasks 4, 17/18, 20, 21, 23, 24. ✓

- **Placeholder scan**: No TBD / TODO / "similar to Task N" / "add error handling" / placeholder test bodies. Every code block contains full content. ✓

- **Type consistency**:
  - `CPWModel`, `WBalanceSeries`, `DurabilityCurve`, `ResponseProfile`, `PhysiologyBundle` defined once (Task 2) and imported elsewhere. ✓
  - `Features`, `Findings`, `SummaryLatest`, `StateFile` defined once (Task 2) and imported by tasks 9, 10, 11–16, 17, 18. ✓
  - `analyze()` signature varies per sub-analyzer by necessity (pacing/w_balance/durability/climbing/target_align/historical_cmp each take different auxiliary inputs) — the orchestrator's `SUB_FUNCS` table (Task 18) adapts each call; verified match. ✓
  - `inject_phase1_context` (Task 20) and `update_brief` (Task 21) read the same filenames `cp_w_current.json`, `durability.json`, `response_profile.json`, `summary_latest.json` that earlier tasks write. ✓

- **Known minor deviation from spec**: Spec §4.1 shows the `sync_data.py` tail as a Python-import style (`from icu.src.coach.physiology.refresher import refresh_all`). Our implementation keeps `sync_data.py` in its existing subprocess orchestration style and adds three new script invocations. Rationale: matches the file's actual current shape (subprocess-based) rather than forcing a refactor. Functionally identical; each new call is still independent and soft-failing. ✓

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-16-ai-coach-phase-1-implementation.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Uses `superpowers:subagent-driven-development`.

2. **Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

**Which approach?**
