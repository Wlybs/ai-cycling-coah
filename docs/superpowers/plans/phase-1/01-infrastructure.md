# Phase 1 — Infrastructure (Tasks 1-3)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

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

