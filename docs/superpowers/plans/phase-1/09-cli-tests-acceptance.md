# Phase 1 — CLI tools, e2e tests, acceptance (Tasks 22-24)

> Part of the Phase 1 implementation plan. See [00-index.md](./00-index.md) for the full plan and execution rules.

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

