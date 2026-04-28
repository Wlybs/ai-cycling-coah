# Phase 3 — Integration + CLI + e2e + acceptance (Tasks T69–T72)

> **Path note:** Plan files at `/mnt/d/Cycling-phase3/docs/superpowers/plans/phase-3/`;
> source under `/mnt/d/Cycling-phase3/icu/`. Code-block paths are relative to
> `/mnt/d/Cycling-phase3/icu/` unless explicitly said otherwise. The T72
> acceptance checklist runs in the **main** repo `/mnt/d/Cycling/icu/` after
> `ai-coach-phase-3` is merged into a release branch — see OQ4 lock.

> **Milestone:** **M1** (per `00-index.md` line 32-33). File 09 closes Phase 3
> M1: integration of ledger ingester + daily_adapt + a small advisory hook
> into `sync_data.py`, an end-to-end fixture-driven smoke test of the entire
> pipeline, and a real-repo acceptance checklist that the user can paste into
> a terminal session in `/mnt/d/Cycling/icu`.

## Mission

Stitch the FROZEN Phase 3 components from Files 01–07 (M1) into the daily
sync pipeline and produce two executable acceptance artefacts:

- A NEW pure-function module `coach/common/action_suggester.py` that emits
  human-readable advisory lines based on 4 trigger conditions read from the
  ledger + deep_analysis. Returns `list[str]` only — never raises, never
  shells out.
- A 3-step extension to `scripts/sync_data.py` (steps 11–13) that runs
  `ingest_ledger.py`, `daily_adapt.py`, and the advisory hook AFTER step 10
  (Phase 1 Coach Brief update) and BEFORE the failures-summary block. Each
  new step is wrapped to soft-fail (warn + continue) so a missing Phase 3
  module never breaks Phase 1/2 sync. This is the ONE allowance under
  PHASE_1_2_IMMUTABILITY (00-index.md decision lock #2).
- An e2e real-fixture test `tests/e2e/test_phase3_full_chain.py` that
  exercises the full chain: seeded Phase 1/2 outputs → ingest_ledger →
  daily_adapt → run_consensus → finalize_consensus (with a frozen Gemini
  response fixture) → apply_adaptation against a mock ICU PATCH endpoint →
  action_suggester replay. Verifies every Phase 3 `decision_type` lands in
  the ledger.
- A markdown-only real-repo acceptance checklist (T72) — exact bash
  commands paired with expected post-conditions. Not a runnable test.

API_FREE invariant: no LLM SDK import, no network in unit tests; the e2e
test mocks ICU PATCH via the File 05 fixture; the T72 checklist is the only
moment a human paste of a Gemini reply is required.

## Out of scope

- Phase 1/2 internals (PHASE_1_2_IMMUTABILITY locked).
- Files 01–08 modules are FROZEN — File 09 imports only. Do NOT add fields
  to `DecisionEntry`, do NOT change `parse(...)`, do NOT touch
  `council_prompt.py` / `strict_prompt.py` / `daily_adapt.run` /
  `apply_adaptation.run` / `LedgerWriter.record`.
- The Phase 1 segment of `scripts/sync_data.py` (steps 1–10) — read-only.
  The ONLY allowed edit is appending steps 11–13 between line 66 (the
  `update_coach_brief.py` call) and line 68 (the `if failures:` block).
- Auto-execution of `run_consensus.py` / `apply_adaptation.py` — these stay
  human-gated (HUMAN_GATE_ON_ICU_WRITE, RED_NO_AUTO_ESCALATE).
- Any new Pydantic models. `action_suggester.suggest_actions(...)` returns
  `list[str]` and `print_suggestions(...)` returns `None` (prints only).
- Any new dependency (NO_NEW_DEPS). Suggester uses stdlib + already-imported
  Phase 3 ledger reader.
- M2 strict-mode tests beyond what File 08 already covers — File 09 e2e uses
  council mode only, per blueprint default.
- `ledger_digest.py` (M2 task, not part of File 09).

## Inputs (read-only contracts)

These exist before File 09 starts. Touching them is a hard violation.

| Path | What File 09 uses |
|---|---|
| `src/coach/ledger/reader.py` | `LedgerReader(path).query(decision_type=..., since=..., until=...)` — for trigger detection. |
| `src/coach/ledger/types.py` | `DecisionType` literal (the 8 enum values). |
| `src/coach/common/logging.py` | `get_logger("suggester") -> JSONLLogger.event(...)` for advisory emission audit. |
| `src/coach/adapter/daily_adapt.py` | `run(...)` signature for soft-fail wrapper validation only — File 09 does not import it; the CLI script `scripts/daily_adapt.py` is invoked via subprocess. |
| `scripts/ingest_ledger.py` | Argparse signature: `--memory <dir> --warehouse <dir> [--ledger <path>]`. |
| `scripts/daily_adapt.py` | Argparse signature: `--date YYYY-MM-DD --memory <dir> --warehouse <dir> [--ledger <path>] [--dry-run]`. The `--dry-run` flag means **NO** writes — useful for the soft-fail wrapper to inspect verdict without polluting ledger. |
| `scripts/run_consensus.py` (File 07) | `--athlete-state <json> --plan <json> --memory <dir> --out <dir> [--with-history]`. |
| `scripts/finalize_consensus.py` (File 07) | `--consensus-dir <dir> --athlete-state <json> --ledger <jsonl> [--confirm]`. |
| `scripts/apply_adaptation.py` (File 05) | `--date YYYY-MM-DD --memory <dir> --warehouse <dir> [--events <json>] [--confirm]`. |
| `tests/fixtures/phase3/adapter/...` (File 05) | mock ICU PATCH server fixture; the e2e test reuses it directly. |

## Outputs (what gets created or extended)

```
icu/src/coach/common/
└── action_suggester.py       ← T69.1 + T69.2 (NEW, ~180 lines impl)

icu/scripts/
└── sync_data.py              ← T70.1 + T70.2 (EDIT — append steps 11-13 ONLY)

icu/tests/unit/coach/common/
└── test_action_suggester.py  ← T69.1 + T69.2 (NEW, ~14 tests)

icu/tests/unit/scripts/
└── test_sync_data_phase3_integration.py  ← T70.1 + T70.2 (NEW, ~8 tests)

icu/tests/e2e/
└── test_phase3_full_chain.py             ← T71.1 + T71.2 (NEW, ~6 tests)

icu/tests/fixtures/phase3/e2e/
├── coach_memory_seed/                    (CREATE)
│   ├── physiology/
│   │   ├── cp_w_current.json
│   │   ├── durability.json
│   │   └── response_profile.json
│   ├── deep_analysis/
│   │   ├── summary_2026-04-21.json
│   │   ├── summary_2026-04-22.json
│   │   ├── summary_2026-04-23.json
│   │   └── summary_latest.json           (symlink-equivalent copy of latest)
│   ├── periodization/
│   │   ├── phase_current.json
│   │   ├── macro_plan.json
│   │   ├── meso_block.json
│   │   └── micro_cycle_2026W17.json
│   └── reports/
│       ├── plan_2026W17.json
│       └── plan_2026W17.trace.json
├── warehouse_seed/                       (CREATE)
│   ├── 1_Profile/athlete.json
│   ├── 2_Wellness/wellness_history.json  (28+ days)
│   └── 8_Events/events.json
└── consensus_response.md                 (frozen Gemini reply, council mode)

docs/superpowers/plans/phase-3/
└── 09-integration-cli-tests.md           ← THIS FILE (CREATE)
```

## Decision-type contract

File 09 writes NO new decision types. The e2e test verifies all eight
existing `DecisionType` literals can be observed in a single ledger after one
end-to-end run:

| decision_type | Source script | When emitted in e2e |
|---|---|---|
| `phase_transition` | `ingest_ledger.py` (File 02) | seeded fixture has phase_current.json with new phase since prior history → ingester back-fills entry |
| `macro_plan_generated` | `ingest_ledger.py` | seeded macro_plan.json |
| `meso_block_created` | `ingest_ledger.py` | seeded meso_block.json |
| `micro_cycle_generated` | `ingest_ledger.py` | seeded micro_cycle_2026W17.json |
| `weekly_plan_assembled` | `ingest_ledger.py` | seeded plan_2026W17.json + trace |
| `adaptation_verdict` | `daily_adapt.py` (File 05) | runs against today's wellness fixture |
| `consensus_verdict` | `finalize_consensus.py` (File 07) | runs after pasting `consensus_response.md` |
| `adaptation_applied` | `apply_adaptation.py --confirm` (File 05) | only IF daily_adapt verdict is red AND mock PATCH endpoint succeeds |

The e2e fixture is intentionally seeded so `daily_adapt` returns `red`,
guaranteeing all 8 decision types appear at least once.

`action_suggester` writes NO ledger entries — it is purely advisory output.

## Touch list (do not exceed)

```
icu/src/coach/common/action_suggester.py                          (CREATE)
icu/scripts/sync_data.py                                          (EDIT — append steps 11-13)
icu/tests/unit/coach/common/test_action_suggester.py              (CREATE)
icu/tests/unit/scripts/test_sync_data_phase3_integration.py       (CREATE)
icu/tests/e2e/test_phase3_full_chain.py                           (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/physiology/cp_w_current.json        (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/physiology/durability.json          (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/physiology/response_profile.json    (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/deep_analysis/summary_2026-04-21.json   (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/deep_analysis/summary_2026-04-22.json   (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/deep_analysis/summary_2026-04-23.json   (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/deep_analysis/summary_latest.json   (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/periodization/phase_current.json    (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/periodization/macro_plan.json       (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/periodization/meso_block.json       (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/periodization/micro_cycle_2026W17.json   (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/reports/plan_2026W17.json           (CREATE)
icu/tests/fixtures/phase3/e2e/coach_memory_seed/reports/plan_2026W17.trace.json     (CREATE)
icu/tests/fixtures/phase3/e2e/warehouse_seed/1_Profile/athlete.json                 (CREATE)
icu/tests/fixtures/phase3/e2e/warehouse_seed/2_Wellness/wellness_history.json       (CREATE)
icu/tests/fixtures/phase3/e2e/warehouse_seed/8_Events/events.json                   (CREATE)
icu/tests/fixtures/phase3/e2e/consensus_response.md                                 (CREATE)
docs/superpowers/plans/phase-3/09-integration-cli-tests.md                          (CREATE — this file)
```

Anything else (especially `src/coach/ledger/`, `src/coach/adapter/`,
`src/coach/consensus/`, `src/coach/physiology/`, `src/coach/deep_analyzer/`,
`src/coach/periodization/`, `src/coach/session_designer/`, the Phase 1
segment of `sync_data.py`) is OFF LIMITS.

`git diff --stat` regression after the final commit must show exactly the
paths above and no others.

## Pre-flight Pydantic+IO checklist

Lifted from File 08; same 9 items, paste into implementer brief. Fail-fast
quality gates.

1. **Frozen Pydantic models.** **File 09 adds NONE — `action_suggester` returns
   plain `list[str]`, no Pydantic models. Adding any BaseModel is almost
   certainly wrong; stop and ask.** Reuse `LedgerReader` to query
   `DecisionEntry` already-frozen models when needed.
2. **Explicit field types**, no bare `Any`; `list[str]` / `dict[str, Any]`
   with comment when truly needed.
3. **No `Optional[T]`** — use `T | None` + explicit `default=None`. Never
   `from typing import Optional`.
4. **UTF-8 explicit** on every read/write/open. The fixture JSON files are
   committed UTF-8; the suggester reads them with `encoding="utf-8"`.
5. **`pathlib.Path`** over `os.path`; compose with `dir / "name.json"`.
   Note: `scripts/sync_data.py` historically uses `os.path` — keep the new
   steps minimal (`subprocess.run` calls only) so we don't have to mix
   styles within one function.
6. **Stable JSON** dumps: `indent=2, sort_keys=True, ensure_ascii=False`
   when fixtures are authored. Suggester does not dump JSON.
7. **Timezone-aware timestamps**: `datetime.now(timezone.utc)`. Never
   `utcnow()`. Suggester accepts `today: date | None = None` for
   determinism in tests.
8. **Immutable defaults**: `default_factory=list/dict`. The
   `suggest_actions(...)` signature uses `today=None` (not `date.today()`)
   so the default isn't evaluated at module import.
9. **Explicit CLI exit codes** (sync_data only): `0` always for the new
   steps. Soft-fail wrapper catches `subprocess.CalledProcessError` AND
   `ImportError` AND `Exception` — all three become append-to-`failures` +
   continue. Phase 1 sync NEVER turns red because of Phase 3.

## Architectural map

```
sync_data.py (extended)
  ├── steps 1-10 (FROZEN — Phase 1/2)
  ├── step 11: subprocess(ingest_ledger.py)         ← T70.1
  ├── step 12: subprocess(daily_adapt.py)           ← T70.1
  ├── step 13: in-process action_suggester          ← T70.2
  │     try:
  │         from src.coach.common.action_suggester import (
  │             suggest_actions, print_suggestions)
  │         lines = suggest_actions(ledger_path, periodization_dir,
  │                                 deep_analysis_dir)
  │         print_suggestions(lines, header="📌 Phase 3 建议")
  │     except ImportError:
  │         print("⚠️  Phase 3 suggester unavailable; skipping.")
  │     except Exception as exc:
  │         print(f"⚠️  suggester failed: {exc}; continuing.")
  │         failures.append("action_suggester")
  └── if failures: print summary  (FROZEN)

action_suggester.py
  suggest_actions(ledger_path, periodization_dir, deep_analysis_dir,
                  today=None) -> list[str]
    ├── _trigger_phase_transition_this_week(reader, today)  ← T69.1
    ├── _trigger_safety_violation_in_latest_plan(reader)    ← T69.1
    ├── _trigger_consensus_overdue(reader, today)           ← T69.1
    └── _trigger_stimulus_score_decline(deep_analysis_dir)  ← T69.1

  print_suggestions(lines, *, header) -> None                ← T69.2
    print(header)
    for line in lines:
        print(f"  • {line}")

e2e/test_phase3_full_chain.py
  T71.1 — fixture authoring + ingester→adapt slice
    ├── seed coach_memory_seed/* + warehouse_seed/* into tmp_path
    ├── subprocess(ingest_ledger.py) → assert ≥5 decision_types
    ├── subprocess(daily_adapt.py) → assert adaptation_verdict + red md +
    │   proposed_session_<date>.json
    └── assert ledger has 6 unique decision_types so far

  T71.2 — consensus → apply → suggester slice
    ├── subprocess(run_consensus.py) → council.prompt.md exists
    ├── shutil.copy(consensus_response.md → council.response.md)
    ├── subprocess(finalize_consensus.py --confirm) → consensus_verdict
    │   in ledger + verdict.md
    ├── subprocess(apply_adaptation.py --date <date> --confirm) against
    │   mock ICU PATCH → adaptation_applied in ledger
    └── invoke action_suggester directly → assert ≥1 line emitted
```

# Task 69 — action_suggester pure function + print formatter

T69 builds the heuristic advisory module. It splits into two RED → GREEN
cycles:

- **T69.1** — pure function `suggest_actions(...)` returning `list[str]`,
  with 4 independent trigger detectors. Tests cover each trigger
  independently + a "no triggers" empty-list case.
- **T69.2** — `print_suggestions(lines, *, header)` formatter (header line
  + indented bullets + silent on empty list).

## T69.1 — `suggest_actions` pure function + 4 trigger detectors

**Goal.** Stand up `src/coach/common/action_suggester.py` with:

- Public entry `suggest_actions(ledger_path: Path, periodization_dir: Path,
  deep_analysis_dir: Path, today: date | None = None) -> list[str]`.
- Module-level constants:
  - `CONSENSUS_OVERDUE_DAYS: int = 14`
  - `STIMULUS_DECLINE_WINDOW: int = 3`
- Four private trigger detectors, each returning a single advisory string
  or `None`:
  - `_trigger_phase_transition_this_week(reader, today) -> str | None`
  - `_trigger_safety_violation_in_latest_plan(reader) -> str | None`
  - `_trigger_consensus_overdue(reader, today) -> str | None`
  - `_trigger_stimulus_score_decline(deep_analysis_dir) -> str | None`
- `suggest_actions(...)` calls all 4 in order, drops `None`, returns the
  concatenated list. The order is stable (matches blueprint "触发方式" order).

Trigger semantics:

1. **phase_transition_this_week** — `reader.query(decision_type="phase_transition",
   since=today-7d, until=today+1d)` returns ≥1 entry → emit
   `"本周 Phase Detector 触发了阶段切换；建议跑 run_consensus.py 复核新阶段计划。"`
2. **safety_violation_in_latest_plan** — query latest `weekly_plan_assembled`
   entry; if its `payload.violations` (list) is non-empty → emit
   `"最近一次 weekly_plan_assembled 含 {N} 条 safety guard violation；建议跑 run_consensus.py 让 Critic 审查。"`
3. **consensus_overdue** — query latest `consensus_verdict`; if absent OR
   `today - entry.timestamp.date() > 14 days` → emit
   `"距上次 consensus_verdict 已超过 14 天；建议跑 run_consensus.py 维护决策审查节奏。"`
4. **stimulus_score_decline** — list `deep_analysis_dir.glob("summary_*.json")`,
   sort by filename (date-encoded), take the last 3. Each older file's
   `stimulus_score` ≥ next newer's → trigger fires. Emits
   `"最近 {WINDOW} 次 deep_analysis stimulus_score 单调下滑；建议核查训练负荷或休息状态。"`
   - Skip `summary_latest.json` from glob (it duplicates the most recent dated
     file). Use stable filename sort. If <3 dated files exist, return None
     (insufficient data).

Reading rules:
- All disk reads use `Path.read_text(encoding="utf-8")` + `json.loads`.
- Missing `ledger.jsonl` / missing `deep_analysis_dir` → trigger returns
  None (not error). The function never raises on missing input; only on
  malformed JSON, which is caller's bug not ours.
- Logger calls: `get_logger("suggester").event(action="suggest", trigger=<name>,
  fired=<bool>)` — once per detector.

**Estimated impl size:** ~180 lines (including docstrings, 4 detectors,
imports, logger).

### Step 1 — Write RED test

Create `icu/tests/unit/coach/common/test_action_suggester.py`:

```python
"""T69.1 RED — action_suggester pure function + 4 trigger detectors."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


def _write_ledger_entry(path: Path, *, decision_type: str, ts: datetime,
                        payload: dict, entry_id: str = "01HABCDEF0123456789ABCDEF",
                        source: str = "test") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {"ctl": 60.0, "atl": 65.0, "tsb": -5.0, "w_prime": 18000,
             "phase": "BUILD", "week_of_year": 17}
    rec = {
        "schema_version": 1,
        "entry_id": entry_id,
        "timestamp": ts.isoformat(),
        "decision_type": decision_type,
        "source": source,
        "athlete_state_ref": state,
        "confidence": None,
        "payload": payload,
        "evidence_refs": [],
        "superseded_by": None,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _ulid(n: int) -> str:
    """Stable monotonic-ish ULID-like 26-char string for tests."""
    return f"01HABCDEF0123456789ABCD{n:02d}"


@pytest.fixture
def empty_dirs(tmp_path: Path) -> dict[str, Path]:
    return {
        "ledger": tmp_path / "ledger" / "decisions.jsonl",
        "periodization": tmp_path / "periodization",
        "deep_analysis": tmp_path / "deep_analysis",
    }


def test_no_triggers_returns_empty_list(empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=date(2026, 4, 28))
    assert out == []


def test_trigger1_phase_transition_within_7_days_fires(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=2),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="phase_transition", ts=ts,
                        payload={"new_phase": "PEAK"}, entry_id=_ulid(1))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("阶段切换" in line for line in out)


def test_trigger1_phase_transition_older_than_7_days_silent(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=20),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="phase_transition", ts=ts,
                        payload={"new_phase": "PEAK"}, entry_id=_ulid(2))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    # Trigger 3 (consensus_overdue) DOES fire because no consensus_verdict
    # was ever recorded — so the list is non-empty, but it should NOT
    # contain the phase-transition line.
    assert not any("阶段切换" in line for line in out)


def test_trigger2_safety_violation_in_latest_plan_fires(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=1),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="weekly_plan_assembled", ts=ts,
                        payload={"violations": ["LOAD_SPIKE", "BACK_TO_BACK_HARD"]},
                        entry_id=_ulid(3))
    # Plus a recent consensus to silence trigger 3
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(4))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("safety guard violation" in line for line in out)


def test_trigger2_silent_when_violations_empty(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=1),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="weekly_plan_assembled", ts=ts,
                        payload={"violations": []}, entry_id=_ulid(5))
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(6))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("safety guard violation" in line for line in out)


def test_trigger3_consensus_overdue_when_never_run(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("consensus_verdict" in line and "14 天" in line for line in out)


def test_trigger3_consensus_overdue_after_14d(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=20),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict", ts=ts,
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(7))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("14 天" in line for line in out)


def test_trigger3_consensus_recent_silent(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=3),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict", ts=ts,
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(8))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("14 天" in line for line in out)


def test_trigger4_stimulus_decline_fires(empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    # 3 dated summaries, monotonic decline (older → newer)
    (da / "summary_2026-04-21.json").write_text(
        json.dumps({"stimulus_score": 0.80}), encoding="utf-8")
    (da / "summary_2026-04-22.json").write_text(
        json.dumps({"stimulus_score": 0.50}), encoding="utf-8")
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    # Quiet trigger 3 with a recent consensus
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(9))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("stimulus_score 单调下滑" in line for line in out)


def test_trigger4_silent_when_increasing(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    (da / "summary_2026-04-21.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    (da / "summary_2026-04-22.json").write_text(
        json.dumps({"stimulus_score": 0.50}), encoding="utf-8")
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.70}), encoding="utf-8")
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(10))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("stimulus_score" in line for line in out)


def test_trigger4_silent_when_fewer_than_3_summaries(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(11))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("stimulus_score" in line for line in out)


def test_trigger4_skips_summary_latest_json(
        empty_dirs: dict[str, Path]) -> None:
    """summary_latest.json must NOT participate in the 3-window."""
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    (da / "summary_latest.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(12))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("stimulus_score" in line for line in out)


def test_today_defaults_to_date_today_when_none(
        empty_dirs: dict[str, Path]) -> None:
    """today=None → uses date.today() at call time, not import time."""
    from src.coach.common.action_suggester import suggest_actions
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=None)
    assert isinstance(out, list)
    assert all(isinstance(line, str) for line in out)


def test_returns_plain_list_str_no_pydantic(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=date(2026, 4, 28))
    assert type(out) is list
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/coach/common/test_action_suggester.py -v
```

Expected error fragment:
```
ModuleNotFoundError: No module named 'src.coach.common.action_suggester'
```

All 14 collected tests fail at the import line.

### Step 3 — Minimal implementation

Create `icu/src/coach/common/action_suggester.py`:

```python
"""Phase 3 — heuristic advisory hook.

Pure function: reads ledger + deep_analysis snapshots, returns a list of
human-readable advisory strings. No side effects beyond a single JSONL log
event per detector. Never raises on missing inputs.

API_FREE: no LLM SDK import. NO_NEW_DEPS: stdlib + Phase 1 logger +
Phase 3 LedgerReader only.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader

CONSENSUS_OVERDUE_DAYS: int = 14
STIMULUS_DECLINE_WINDOW: int = 3


def suggest_actions(
    ledger_path: Path,
    periodization_dir: Path,
    deep_analysis_dir: Path,
    today: date | None = None,
) -> list[str]:
    """Return advisory lines based on 4 trigger conditions.

    Triggers (in stable order):
      1. phase_transition entry within last 7 days
      2. latest weekly_plan_assembled has non-empty payload.violations
      3. consensus_verdict absent OR older than CONSENSUS_OVERDUE_DAYS
      4. last STIMULUS_DECLINE_WINDOW dated deep_analysis summaries strictly
         monotonic non-increasing in stimulus_score

    Returns list[str] (possibly empty). Never raises on missing inputs.
    """
    if today is None:
        today = date.today()
    logger = get_logger("suggester")
    reader: LedgerReader | None
    if ledger_path.exists():
        reader = LedgerReader(ledger_path)
    else:
        reader = None

    out: list[str] = []
    for name, fn in (
        ("phase_transition_this_week",
         lambda: _trigger_phase_transition_this_week(reader, today)),
        ("safety_violation_in_latest_plan",
         lambda: _trigger_safety_violation_in_latest_plan(reader)),
        ("consensus_overdue",
         lambda: _trigger_consensus_overdue(reader, today)),
        ("stimulus_score_decline",
         lambda: _trigger_stimulus_score_decline(deep_analysis_dir)),
    ):
        line = fn()
        logger.event(action="suggest", trigger=name, fired=bool(line))
        if line is not None:
            out.append(line)
    return out


def _trigger_phase_transition_this_week(
    reader: LedgerReader | None, today: date,
) -> str | None:
    if reader is None:
        return None
    since = datetime.combine(today - timedelta(days=7), time.min,
                             tzinfo=timezone.utc)
    until = datetime.combine(today + timedelta(days=1), time.min,
                             tzinfo=timezone.utc)
    hits = reader.query(decision_type="phase_transition",
                        since=since, until=until)
    if not hits:
        return None
    return ("本周 Phase Detector 触发了阶段切换；"
            "建议跑 run_consensus.py 复核新阶段计划。")


def _trigger_safety_violation_in_latest_plan(
    reader: LedgerReader | None,
) -> str | None:
    if reader is None:
        return None
    hits = reader.query(decision_type="weekly_plan_assembled")
    if not hits:
        return None
    latest = hits[-1]
    violations = (latest.payload or {}).get("violations", [])
    if not isinstance(violations, list) or not violations:
        return None
    return (f"最近一次 weekly_plan_assembled 含 {len(violations)} 条 "
            f"safety guard violation；建议跑 run_consensus.py 让 Critic 审查。")


def _trigger_consensus_overdue(
    reader: LedgerReader | None, today: date,
) -> str | None:
    if reader is None:
        # No ledger ⇒ never run consensus ⇒ overdue.
        return (f"距上次 consensus_verdict 已超过 "
                f"{CONSENSUS_OVERDUE_DAYS} 天；"
                f"建议跑 run_consensus.py 维护决策审查节奏。")
    hits = reader.query(decision_type="consensus_verdict")
    if not hits:
        return (f"距上次 consensus_verdict 已超过 "
                f"{CONSENSUS_OVERDUE_DAYS} 天；"
                f"建议跑 run_consensus.py 维护决策审查节奏。")
    latest = hits[-1]
    age_days = (today - latest.timestamp.date()).days
    if age_days > CONSENSUS_OVERDUE_DAYS:
        return (f"距上次 consensus_verdict 已超过 "
                f"{CONSENSUS_OVERDUE_DAYS} 天；"
                f"建议跑 run_consensus.py 维护决策审查节奏。")
    return None


def _trigger_stimulus_score_decline(deep_analysis_dir: Path) -> str | None:
    if not deep_analysis_dir.exists():
        return None
    dated = sorted(
        p for p in deep_analysis_dir.glob("summary_*.json")
        if p.name != "summary_latest.json"
    )
    if len(dated) < STIMULUS_DECLINE_WINDOW:
        return None
    window = dated[-STIMULUS_DECLINE_WINDOW:]
    scores: list[float] = []
    for p in window:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            scores.append(float(doc.get("stimulus_score")))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    monotonic_non_increasing = all(
        scores[i] >= scores[i + 1] for i in range(len(scores) - 1)
    )
    strictly_decreasing_overall = scores[0] > scores[-1]
    if monotonic_non_increasing and strictly_decreasing_overall:
        return (f"最近 {STIMULUS_DECLINE_WINDOW} 次 deep_analysis "
                f"stimulus_score 单调下滑；建议核查训练负荷或休息状态。")
    return None
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/coach/common/test_action_suggester.py -v
```

Expected: 14 passed.

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/src/coach/common/action_suggester.py \
          icu/tests/unit/coach/common/test_action_suggester.py && \
  git commit -m "feat(coach-phase3): T69.1 action_suggester pure function + 4 trigger detectors"
```

## T69.2 — `print_suggestions` formatter

**Goal.** Add the `print_suggestions(lines, *, header)` formatter to
`action_suggester.py`. It prefixes a header line and indents each suggestion
with a bullet. On empty list, prints nothing (silent).

### Step 1 — Write RED test

Append to `icu/tests/unit/coach/common/test_action_suggester.py`:

```python
def test_print_suggestions_silent_on_empty(capsys) -> None:
    from src.coach.common.action_suggester import print_suggestions
    print_suggestions([], header="📌 Phase 3 建议")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_suggestions_renders_header_and_bullets(capsys) -> None:
    from src.coach.common.action_suggester import print_suggestions
    print_suggestions(["第一条建议", "第二条建议"], header="📌 Phase 3 建议")
    captured = capsys.readouterr()
    assert "📌 Phase 3 建议" in captured.out
    assert "  • 第一条建议" in captured.out
    assert "  • 第二条建议" in captured.out
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/coach/common/test_action_suggester.py::test_print_suggestions_silent_on_empty \
    tests/unit/coach/common/test_action_suggester.py::test_print_suggestions_renders_header_and_bullets -v
```

Expected error fragment:
```
ImportError: cannot import name 'print_suggestions' from 'src.coach.common.action_suggester'
```

### Step 3 — Minimal implementation

Append to `icu/src/coach/common/action_suggester.py`:

```python
def print_suggestions(lines: list[str], *, header: str) -> None:
    """Print header + indented bullets; silent when lines is empty.

    Pure stdout side effect. Never raises.
    """
    if not lines:
        return
    print(header)
    for line in lines:
        print(f"  • {line}")
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/coach/common/test_action_suggester.py -v
```

Expected: 16 passed (14 from T69.1 + 2 from T69.2).

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/src/coach/common/action_suggester.py \
          icu/tests/unit/coach/common/test_action_suggester.py && \
  git commit -m "feat(coach-phase3): T69.2 action_suggester print_suggestions formatter"
```

# Task 70 — `sync_data.py` tail integration (steps 11-13)

T70 wires the Phase 3 components into the existing `sync_data.py`
orchestrator. The edit is strictly an APPEND between line 66 (the existing
step-10 `update_coach_brief.py` call) and line 68 (the existing
`if failures:` block). PHASE_1_2_IMMUTABILITY allows this single allowance
per 00-index.md decision lock #2; we cite it inline in the script comment.

T70 splits into 2 RED → GREEN cycles:

- **T70.1** — wire steps 11 + 12 (subprocess invocations of `ingest_ledger.py`
  and `daily_adapt.py`). Verify ordering, soft-fail on either, and that
  ingester failure does not abort daily_adapt.
- **T70.2** — wire step 13 (in-process import of action_suggester). Verify
  ImportError swallowed with warning; verify `failures` list grows on
  unexpected exception.

## T70.1 — sync_data steps 11 + 12 (subprocess: ingest_ledger + daily_adapt)

**Goal.** Append two `run_script(...)` calls to `main()` in
`scripts/sync_data.py`, sandwiched between the existing step 10 and the
`if failures:` summary. Each call uses the identical
`subprocess.run(check=True)` + try/except already present in `run_script`.
PHASE_1_2_IMMUTABILITY allowance applies: we ONLY append; we do not modify
existing lines.

The ingest_ledger CLI requires `--memory <dir> --warehouse <dir>`. Compute
both via `os.path.dirname(SCRIPTS_DIR)` (= `/mnt/d/Cycling/icu/`) joined
with `coach_memory` and `icu_data_warehouse` respectively. The daily_adapt
CLI also wants `--date YYYY-MM-DD`; default to today via
`datetime.now(timezone.utc).date().isoformat()`.

### Step 1 — Write RED test

Create `icu/tests/unit/scripts/test_sync_data_phase3_integration.py`:

```python
"""T70.1 RED — sync_data.py steps 11 + 12 wiring."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


def _import_main():
    """Import sync_data.main fresh each call — module is a script."""
    import importlib
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    import sync_data  # type: ignore
    importlib.reload(sync_data)
    return sync_data


def test_step11_invokes_ingest_ledger() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    invoked = [c for c in captured if any("ingest_ledger.py" in p for p in c)]
    assert len(invoked) == 1, f"ingest_ledger.py should be invoked exactly once: {captured}"
    assert "--memory" in invoked[0]
    assert "--warehouse" in invoked[0]


def test_step12_invokes_daily_adapt() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    invoked = [c for c in captured if any("daily_adapt.py" in p for p in c)]
    assert len(invoked) == 1
    assert "--date" in invoked[0]
    assert "--memory" in invoked[0]
    assert "--warehouse" in invoked[0]


def test_step11_then_step12_order_preserved() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    idx_ingest = next(i for i, c in enumerate(captured)
                      if any("ingest_ledger.py" in p for p in c))
    idx_adapt = next(i for i, c in enumerate(captured)
                     if any("daily_adapt.py" in p for p in c))
    assert idx_ingest < idx_adapt


def test_step11_failure_does_not_abort_step12() -> None:
    sd = _import_main()
    captured: list[list[str]] = []

    def fake_run(cmd, check=True, **kw):
        captured.append([str(c) for c in cmd])
        if any("ingest_ledger.py" in p for p in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    assert any("daily_adapt.py" in p for c in captured for p in c), (
        "daily_adapt.py must still run after ingest_ledger.py failure"
    )
    assert "ingest_ledger.py" in sd.failures
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_sync_data_phase3_integration.py -v
```

Expected error fragment:
```
AssertionError: ingest_ledger.py should be invoked exactly once: [...]
```

(The current `sync_data.py` does not invoke ingest_ledger.py at all.)

### Step 3 — Minimal implementation

Edit `icu/scripts/sync_data.py`. **Do not** modify existing lines 1–66.
**Append** the following block between the existing line 66 (the
`run_script("update_coach_brief.py")` call's closing line) and line 68
(the `if failures:` block):

```python
    # ---------------------------------------------------------------
    # Phase 3 tail integration (steps 11–13)
    # PHASE_1_2_IMMUTABILITY allowance per docs/superpowers/plans/
    # phase-3/00-index.md decision lock #2: this is the ONE permitted
    # extension point — append-only after step 10, before failures
    # summary. Each step is soft-fail; Phase 1/2 sync never goes red
    # because of Phase 3 (per 00-index.md execution rule #8).
    # ---------------------------------------------------------------
    from datetime import datetime, timezone
    REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
    MEMORY_DIR = os.path.join(REPO_ROOT, "coach_memory")
    WAREHOUSE_DIR = os.path.join(REPO_ROOT, "icu_data_warehouse")
    TODAY = datetime.now(timezone.utc).date().isoformat()

    # 11. Phase 3 — Ledger ingester (back-fill from Phase 2 artefacts)
    run_script("ingest_ledger.py",
               ["--memory", MEMORY_DIR, "--warehouse", WAREHOUSE_DIR])

    # 12. Phase 3 — Daily adaptation (4-signal evaluation)
    run_script("daily_adapt.py",
               ["--date", TODAY,
                "--memory", MEMORY_DIR, "--warehouse", WAREHOUSE_DIR])
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_sync_data_phase3_integration.py -v
```

Expected: 4 passed.

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/scripts/sync_data.py \
          icu/tests/unit/scripts/test_sync_data_phase3_integration.py && \
  git commit -m "feat(coach-phase3): T70.1 sync_data steps 11-12 ingest + adapt"
```

## T70.2 — sync_data step 13 (in-process action_suggester import-soft)

**Goal.** Append step 13 — an in-process call to
`action_suggester.suggest_actions(...) + print_suggestions(...)` — to
`scripts/sync_data.py`, immediately after step 12 and before the
`if failures:` block. The call is wrapped in try/except handling
`ImportError` (Phase 3 not installed → warn + skip, do NOT add to
failures) and any other `Exception` (real bug → warn + add to failures).

### Step 1 — Write RED test

Append to `icu/tests/unit/scripts/test_sync_data_phase3_integration.py`:

```python
def test_step13_invokes_action_suggester(capsys) -> None:
    sd = _import_main()
    captured_calls: list[tuple] = []

    def fake_run(cmd, check=True, **kw):
        class _R: returncode = 0
        return _R()

    fake_module = type("M", (), {})()
    fake_module.suggest_actions = lambda *a, **kw: (
        captured_calls.append(("suggest", a, kw)) or ["建议一", "建议二"]
    )
    fake_module.print_suggestions = lambda lines, *, header: (
        captured_calls.append(("print", lines, header))
    )

    import sys
    sys.modules["src.coach.common.action_suggester"] = fake_module

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    suggest_calls = [c for c in captured_calls if c[0] == "suggest"]
    print_calls = [c for c in captured_calls if c[0] == "print"]
    assert len(suggest_calls) == 1
    assert len(print_calls) == 1
    assert print_calls[0][1] == ["建议一", "建议二"]

    del sys.modules["src.coach.common.action_suggester"]


def test_step13_import_error_swallowed_does_not_add_to_failures(
        capsys) -> None:
    sd = _import_main()

    def fake_run(cmd, check=True, **kw):
        class _R: returncode = 0
        return _R()

    import builtins
    real_import = builtins.__import__

    def boom(name, *a, **kw):
        if "action_suggester" in name:
            raise ImportError(f"No module named {name}")
        return real_import(name, *a, **kw)

    with patch.object(builtins, "__import__", side_effect=boom), \
         patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    assert "action_suggester" not in sd.failures
    captured = capsys.readouterr()
    assert "Phase 3 suggester unavailable" in captured.out


def test_step13_unexpected_exception_added_to_failures(capsys) -> None:
    sd = _import_main()

    def fake_run(cmd, check=True, **kw):
        class _R: returncode = 0
        return _R()

    fake_module = type("M", (), {})()
    fake_module.suggest_actions = lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("ledger corrupt")
    )
    fake_module.print_suggestions = lambda lines, *, header: None

    import sys
    sys.modules["src.coach.common.action_suggester"] = fake_module

    with patch.object(subprocess, "run", side_effect=fake_run):
        sd.main()

    assert "action_suggester" in sd.failures
    captured = capsys.readouterr()
    assert "suggester failed" in captured.out

    del sys.modules["src.coach.common.action_suggester"]


def test_main_exit_does_not_raise_when_phase3_step_fails(capsys) -> None:
    """Phase 1/2 sync MUST stay green even when Phase 3 explodes."""
    sd = _import_main()

    def fake_run(cmd, check=True, **kw):
        if any("ingest_ledger.py" in p for p in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
        class _R: returncode = 0
        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        # Must not raise SystemExit non-zero / propagate exceptions
        sd.main()
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_sync_data_phase3_integration.py::test_step13_invokes_action_suggester \
    tests/unit/scripts/test_sync_data_phase3_integration.py::test_step13_import_error_swallowed_does_not_add_to_failures \
    tests/unit/scripts/test_sync_data_phase3_integration.py::test_step13_unexpected_exception_added_to_failures \
    tests/unit/scripts/test_sync_data_phase3_integration.py::test_main_exit_does_not_raise_when_phase3_step_fails \
    -v
```

Expected: 4 failures with messages like `len(suggest_calls) == 1` →
actual 0 (current sync_data does not call action_suggester).

### Step 3 — Minimal implementation

Append to `icu/scripts/sync_data.py` immediately after the
`run_script("daily_adapt.py", [...])` call from T70.1 and before the
`if failures:` block:

```python
    # 13. Phase 3 — Action suggester (in-process, soft-fail on ImportError)
    try:
        from src.coach.common.action_suggester import (
            suggest_actions, print_suggestions,
        )
        from pathlib import Path as _Path
        ledger_path = _Path(MEMORY_DIR) / "ledger" / "decisions.jsonl"
        periodization_dir = _Path(MEMORY_DIR) / "periodization"
        deep_analysis_dir = _Path(MEMORY_DIR) / "deep_analysis"
        try:
            lines = suggest_actions(ledger_path, periodization_dir,
                                     deep_analysis_dir)
            print_suggestions(lines, header="📌 Phase 3 建议")
        except Exception as exc:  # noqa: BLE001 — soft-fail boundary
            print(f"⚠️  suggester failed: {exc}; continuing.")
            failures.append("action_suggester")
    except ImportError:
        print("⚠️  Phase 3 suggester unavailable; skipping.")
```

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/unit/scripts/test_sync_data_phase3_integration.py -v
```

Expected: 8 passed (4 from T70.1 + 4 from T70.2).

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/scripts/sync_data.py \
          icu/tests/unit/scripts/test_sync_data_phase3_integration.py && \
  git commit -m "feat(coach-phase3): T70.2 sync_data step 13 suggester import-soft"
```

# Task 71 — e2e real-fixture full chain test

T71 builds the end-to-end smoke test exercising the entire Phase 3 pipeline
against a frozen fixture tree under `tests/fixtures/phase3/e2e/`. The test
seeds the fixture tree into a `tmp_path` working directory (cp -r style),
then invokes each Phase 3 CLI in sequence via `subprocess.run`. The mock
ICU PATCH endpoint (already authored under File 05's
`tests/fixtures/phase3/adapter/`) is reused for `apply_adaptation.py
--confirm`.

The fixture is intentionally seeded so the daily verdict is `red`. This
guarantees `apply_adaptation` has a `proposed_session_<date>.json` to push
and we exercise the full `adaptation_applied` path. It also guarantees one
`phase_transition` entry will land within the past week (trigger #1), so
the suggester emits at least one line.

T71 splits into 2 RED → GREEN cycles:

- **T71.1** — fixture authoring + `ingest_ledger` → `daily_adapt` slice
  (assert ledger contains the 6 ingester decision_types + adapter verdict).
- **T71.2** — `run_consensus` → `finalize_consensus` (with frozen Gemini
  reply) → `apply_adaptation --confirm` → `action_suggester` slice (assert
  all 8 decision_types + at least one suggestion).

## T71.1 — fixtures + ingester→adapt slice

**Goal.** Author the entire fixture tree under
`tests/fixtures/phase3/e2e/` plus a single test that copies it to
`tmp_path`, invokes `scripts/ingest_ledger.py` and `scripts/daily_adapt.py`
as subprocesses against the tmp paths, and asserts:

1. `ingest_ledger` exits 0 and writes ≥5 distinct decision_types to the
   tmp ledger (all five Phase-2-derived types).
2. `daily_adapt` exits 0 and writes one `adaptation_verdict` entry with
   `payload.verdict == "red"`.
3. `proposed_session_<date>.json` exists on disk under tmp adapter dir.
4. `today_<date>.md` exists.

### Step 1 — Write RED test

Create `icu/tests/e2e/test_phase3_full_chain.py`:

```python
"""T71 e2e — Phase 3 full chain smoke test against frozen fixtures."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ICU = Path(__file__).resolve().parents[2]  # /mnt/d/Cycling-phase3/icu
FIXTURE_ROOT = REPO_ICU / "tests" / "fixtures" / "phase3" / "e2e"
PYTHON = sys.executable


def _seed_workspace(tmp_path: Path) -> dict[str, Path]:
    """Copy frozen fixture tree into tmp_path and return path map."""
    memory = tmp_path / "coach_memory"
    warehouse = tmp_path / "icu_data_warehouse"
    shutil.copytree(FIXTURE_ROOT / "coach_memory_seed", memory)
    shutil.copytree(FIXTURE_ROOT / "warehouse_seed", warehouse)
    (memory / "ledger").mkdir(parents=True, exist_ok=True)
    (memory / "adapter").mkdir(parents=True, exist_ok=True)
    return {
        "memory": memory,
        "warehouse": warehouse,
        "ledger": memory / "ledger" / "decisions.jsonl",
        "adapter": memory / "adapter",
    }


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    return _seed_workspace(tmp_path)


@pytest.mark.e2e
def test_ingest_ledger_seeds_five_decision_types(
        workspace: dict[str, Path]) -> None:
    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    assert result.returncode == 0, result.stderr
    entries = _read_ledger(workspace["ledger"])
    types_seen = {e["decision_type"] for e in entries}
    expected = {"phase_transition", "macro_plan_generated",
                "meso_block_created", "micro_cycle_generated",
                "weekly_plan_assembled"}
    assert expected <= types_seen, f"missing: {expected - types_seen}"


@pytest.mark.e2e
def test_daily_adapt_red_verdict_writes_proposed_session(
        workspace: dict[str, Path]) -> None:
    # Pre-seed ledger via ingest_ledger so adapter sees Phase 2 history
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )

    target_date = date(2026, 4, 28).isoformat()  # matches fixture today
    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "daily_adapt.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    assert result.returncode == 0, result.stderr

    entries = _read_ledger(workspace["ledger"])
    verdicts = [e for e in entries
                if e["decision_type"] == "adaptation_verdict"]
    assert len(verdicts) >= 1
    assert verdicts[-1]["payload"]["verdict"] == "red"

    md_path = workspace["adapter"] / f"today_{target_date}.md"
    proposed = workspace["adapter"] / f"proposed_session_{target_date}.json"
    assert md_path.exists()
    assert proposed.exists()
```

The fixture authoring is the bulk of the work. Author the following files
verbatim (compact JSON, UTF-8). The values are deliberately chosen to:

- seed 5 ingester decision types (all five Phase-2-derived);
- have wellness on `2026-04-28` so `daily_adapt` triggers the red rule
  (e.g., HRV deviation > 10 % below 7-day mean + sleep < 6 h + soreness
  > 3 / 5 — adjust based on File 03 `rules.py` thresholds);
- have a recent `phase_transition` (yesterday) so suggester trigger #1
  fires in T71.2.

`coach_memory_seed/physiology/cp_w_current.json`:
```json
{
  "cp_watts": 288,
  "w_prime_joules": 18000,
  "athlete_ftp_set": 288,
  "computed_at": "2026-04-21T00:00:00+00:00"
}
```

`coach_memory_seed/physiology/durability.json`:
```json
{
  "decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1},
  "sample_size_rides": 24,
  "computed_at": "2026-04-21T00:00:00+00:00"
}
```

`coach_memory_seed/physiology/response_profile.json`:
```json
{
  "types": {
    "VO2max": {"tolerance_class": "high"},
    "Threshold": {"tolerance_class": "high"},
    "Endurance": {"tolerance_class": "high"}
  },
  "knee_loading": {"flag": false},
  "computed_at": "2026-04-21T00:00:00+00:00"
}
```

`coach_memory_seed/deep_analysis/summary_2026-04-21.json`:
```json
{
  "headline_verdict": "stable",
  "stimulus_score": 0.72,
  "progression_flag": "ok",
  "knee_flag": false
}
```

`coach_memory_seed/deep_analysis/summary_2026-04-22.json`:
```json
{
  "headline_verdict": "stable",
  "stimulus_score": 0.55,
  "progression_flag": "ok",
  "knee_flag": false
}
```

`coach_memory_seed/deep_analysis/summary_2026-04-23.json`:
```json
{
  "headline_verdict": "declining",
  "stimulus_score": 0.30,
  "progression_flag": "watch",
  "knee_flag": false
}
```

`coach_memory_seed/deep_analysis/summary_latest.json` — copy of
`summary_2026-04-23.json`.

`coach_memory_seed/periodization/phase_current.json`:
```json
{
  "current_phase": "BUILD",
  "transition_reasons": ["TSB recovered to -2", "CTL trending up"],
  "transitioned_at": "2026-04-27T00:00:00+00:00"
}
```

`coach_memory_seed/periodization/macro_plan.json`:
```json
{
  "generated_at": "2026-04-21T00:00:00+00:00",
  "season": "2026",
  "phases": [{"name": "BUILD", "weeks": 4}, {"name": "PEAK", "weeks": 2}]
}
```

`coach_memory_seed/periodization/meso_block.json`:
```json
{
  "block_id": "BUILD-2026W17",
  "generated_at": "2026-04-21T00:00:00+00:00",
  "weeks": 4
}
```

`coach_memory_seed/periodization/micro_cycle_2026W17.json`:
```json
{
  "week_id": "2026W17",
  "phase": "BUILD",
  "days": [
    {"date": "2026-04-27", "intent": "Endurance"},
    {"date": "2026-04-28", "intent": "VO2max"},
    {"date": "2026-04-29", "intent": "Recovery"},
    {"date": "2026-04-30", "intent": "Threshold"},
    {"date": "2026-05-01", "intent": "Endurance"},
    {"date": "2026-05-02", "intent": "Long"},
    {"date": "2026-05-03", "intent": "Rest"}
  ]
}
```

`coach_memory_seed/reports/plan_2026W17.json`:
```json
{
  "plan_period": "2026-W17",
  "weekly_tss_target": 380,
  "days": [
    {"day": "Mon", "training_type": "Endurance", "duration_min": 90,
     "tier": "MEDIUM"},
    {"day": "Tue", "training_type": "VO2max", "duration_min": 75,
     "tier": "HIGH"},
    {"day": "Wed", "training_type": "Recovery", "duration_min": 45,
     "tier": "LOW"},
    {"day": "Thu", "training_type": "Threshold", "duration_min": 90,
     "tier": "HIGH"},
    {"day": "Fri", "training_type": "Endurance", "duration_min": 60,
     "tier": "MEDIUM"},
    {"day": "Sat", "training_type": "Long", "duration_min": 180,
     "tier": "MEDIUM"},
    {"day": "Sun", "training_type": "Rest", "duration_min": 0,
     "tier": "REST"}
  ]
}
```

`coach_memory_seed/reports/plan_2026W17.trace.json`:
```json
{
  "plan_period": "2026-W17",
  "violations": [],
  "session_origins": []
}
```

`warehouse_seed/1_Profile/athlete.json`:
```json
{
  "ftp": 288,
  "hr_max": 188,
  "weight": 62.0,
  "name": "Test Athlete"
}
```

`warehouse_seed/2_Wellness/wellness_history.json` — array of ≥28 daily
entries ending on `2026-04-28`. The 28-day baseline must produce a
`red` verdict on `2026-04-28`. Use the historical baseline (HRV mean ≈ 70,
restingHR mean ≈ 50, sleep mean ≈ 7 h, soreness mean ≈ 1.5) and seed the
final entry with a deliberate red profile:
```json
[
  {"date": "2026-04-01", "hrv": 70, "restingHR": 50, "sleepSecs": 25200,
   "soreness": 1, "fatigue": 1, "stress": 1, "mood": 4, "ctl": 60.0,
   "atl": 60.0},
  ...
  {"date": "2026-04-27", "hrv": 71, "restingHR": 51, "sleepSecs": 26000,
   "soreness": 1, "fatigue": 1, "stress": 2, "mood": 4, "ctl": 65.0,
   "atl": 67.0},
  {"date": "2026-04-28", "hrv": 55, "restingHR": 62, "sleepSecs": 18000,
   "soreness": 4, "fatigue": 4, "stress": 4, "mood": 2, "ctl": 65.0,
   "atl": 75.0}
]
```

(Author the full 28-day series with mostly-baseline numbers; only the last
day deviates. The implementer should run File 03's `rules.py` against the
final fixture by hand once before committing to confirm `verdict == "red"`.)

`warehouse_seed/8_Events/events.json`:
```json
[
  {"id": 99001, "start_date_local": "2026-04-28T07:00:00",
   "category": "WORKOUT", "name": "VO2max Intervals"}
]
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/e2e/test_phase3_full_chain.py -v -m e2e
```

Expected error fragment:
```
FileNotFoundError: [Errno 2] No such file or directory:
  '.../tests/fixtures/phase3/e2e/coach_memory_seed'
```

### Step 3 — Minimal implementation

There is **no source code** to implement for T71.1 — the entire deliverable
is fixture authoring. Author the JSON files listed above. Verify that:

- `ingest_ledger.py` against the seeded tree writes ≥5 decision types.
- `daily_adapt.py --date 2026-04-28` against the seeded tree produces a
  red verdict (smoke-check by running once before committing).

If `daily_adapt` does not return red with the seeded wellness, tune the
last wellness entry until it does — do NOT modify File 03 `rules.py`.

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/e2e/test_phase3_full_chain.py -v -m e2e
```

Expected: 2 passed (the two e2e tests authored above).

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/tests/e2e/test_phase3_full_chain.py \
          icu/tests/fixtures/phase3/e2e/ && \
  git commit -m "test(coach-phase3): T71.1 e2e fixtures + ingester→adapt slice"
```

## T71.2 — consensus → apply → suggester slice

**Goal.** Author the frozen Gemini council reply
(`consensus_response.md`) and 4 additional e2e tests that drive
`run_consensus.py` → `finalize_consensus.py --confirm` →
`apply_adaptation.py --confirm` (against the File 05 mock ICU client) →
direct in-process call to `action_suggester.suggest_actions`. Asserts:

1. `run_consensus.py` writes `council.prompt.md`.
2. `finalize_consensus.py --confirm` writes a `consensus_verdict` ledger
   entry + `verdict.md`.
3. `apply_adaptation.py --confirm` writes an `adaptation_applied` ledger
   entry (mock ICU client returns 200).
4. After all writes, the ledger contains all 8 distinct
   `decision_type` values.
5. `suggest_actions(...)` returns ≥1 line (trigger #1 fires because the
   fixture seeded a `phase_transition` entry within the past 7 days).

### Step 1 — Write RED test

Author `icu/tests/fixtures/phase3/e2e/consensus_response.md`. Must satisfy
File 06's `parse(..., mode="council")` 6 hard rules (≥3 critic points,
≥3-of-4 physiologist keywords, ACCEPT/REVISE/REJECT verdict, confidence
in [0,1], all 4 role tags, valid `<summary_json>` block):

```markdown
<planner>
本周 plan_period 2026-W17 BUILD 阶段：
- Tue VO2max 75 min @ 110% FTP（5×4min on / 3min off）
- Thu Threshold 90 min @ 95% FTP（3×16min on / 5min off）
- Sat Long 180 min @ 65% FTP zone 2

数值依据：(1) 周 TSS 380 与 CTL 65 相符（target 5–6× CTL）；(2) HARD 日 2 次匹配 BUILD 配额下限。
</planner>

<critic>
关键反对：

1. **HARD 日数仅达底线**（数据：BUILD 阶段配额 2–3 次，本周 2 次 = 底线；上周 stimulus_score 0.30 在下滑）。建议加 1 次 race-sim sub-Threshold session 替换 Fri Endurance。
2. **VO2max 工作时长偏低**（数据：5×4 = 20 min，response_profile.types.VO2max.tolerance_class=high 应配 22–24 min）。建议升至 6×4 min。
3. **Sat Long 强度模糊**（数据：180 min @ 65% FTP 没有任何 surge / over-under 段，与 race profile 不一致）。建议在 Long 中段加 3×8min @ 90% FTP 段。
</critic>

<physiologist>
- CP=288W, W'=18000J, durability decay 60s=1.5%/1000kJ — 高强度耐受良好。
- response_profile.types.VO2max.tolerance_class=high 支持 6×4min 升级。
- W' balance 周末估算（Sat 180min long 含 surge）可控制在 −40% 内不破红线。
- knee_flag=false，无关节风险护栏触发。
</physiologist>

<arbiter>
verdict: REVISE
confidence: 0.78
justification: VO2max 工作时长偏低 + HARD 日数不足，建议本周补齐到 22 min + 加一次 race-sim。
revisions:
- day: Tue, from: "5×4min @110%", to: "6×4min @110%"
- day: Fri, from: "Endurance 60min", to: "Threshold sub 75min @92% FTP"
</arbiter>

<summary_json>
{
  "verdict": "REVISE",
  "confidence": 0.78,
  "justification": "VO2max 工作时长偏低 + HARD 日数不足；建议补齐 22 min + 加一次 race-sim。",
  "critic_hard_points": [
    "HARD 日数仅达底线",
    "VO2max 工作时长偏低",
    "Sat Long 强度模糊"
  ],
  "physiologist_keywords_used": ["CP", "W'", "durability", "response_profile"],
  "revisions": [
    {"day": "Tue", "from": "5×4min @110%", "to": "6×4min @110%"},
    {"day": "Fri", "from": "Endurance 60min",
     "to": "Threshold sub 75min @92% FTP"}
  ]
}
</summary_json>
```

Append to `icu/tests/e2e/test_phase3_full_chain.py`:

```python
@pytest.mark.e2e
def test_run_consensus_emits_prompt(workspace: dict[str, Path],
                                     tmp_path: Path) -> None:
    consensus_dir = tmp_path / "consensus_run"
    # Pre-seed ledger
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )
    # Build athlete_state JSON for run_consensus
    athlete_state = tmp_path / "athlete_state.json"
    athlete_state.write_text(json.dumps({
        "ctl": 65.0, "atl": 67.0, "tsb": -2.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    }), encoding="utf-8")

    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "run_consensus.py"),
         "--athlete-state", str(athlete_state),
         "--plan", str(workspace["memory"] / "reports" / "plan_2026W17.json"),
         "--memory", str(workspace["memory"]),
         "--out", str(consensus_dir)],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    assert result.returncode == 0, result.stderr
    assert (consensus_dir / "council.prompt.md").exists()


@pytest.mark.e2e
def test_finalize_consensus_writes_verdict(workspace: dict[str, Path],
                                            tmp_path: Path) -> None:
    consensus_dir = tmp_path / "consensus_run"
    consensus_dir.mkdir(parents=True)
    # Drop the frozen response into council.response.md
    response_md = (FIXTURE_ROOT / "consensus_response.md").read_text(
        encoding="utf-8")
    (consensus_dir / "council.response.md").write_text(response_md,
                                                       encoding="utf-8")
    athlete_state = tmp_path / "athlete_state.json"
    athlete_state.write_text(json.dumps({
        "ctl": 65.0, "atl": 67.0, "tsb": -2.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    }), encoding="utf-8")

    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "finalize_consensus.py"),
         "--consensus-dir", str(consensus_dir),
         "--athlete-state", str(athlete_state),
         "--ledger", str(workspace["ledger"]),
         "--confirm"],
        capture_output=True, text=True, cwd=str(REPO_ICU),
    )
    assert result.returncode == 0, result.stderr
    assert (consensus_dir / "verdict.md").exists()
    entries = _read_ledger(workspace["ledger"])
    verdicts = [e for e in entries
                if e["decision_type"] == "consensus_verdict"]
    assert len(verdicts) >= 1


@pytest.mark.e2e
def test_apply_adaptation_writes_adaptation_applied(
        workspace: dict[str, Path], tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    # Pre-seed via ingest + adapt to get red verdict + proposed_session
    target_date = "2026-04-28"
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "daily_adapt.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )

    # Mock ICU PATCH via env or monkeypatch on ICUClient.update_event
    # File 05 fixture provides the mock; we monkeypatch directly here.
    monkeypatch.setenv("ICU_DRY_RUN_PATCH", "1")
    # Implementer note: if File 05's apply_adaptation honours
    # ICU_DRY_RUN_PATCH env, this is sufficient. Otherwise, monkeypatch
    # src.fetcher.icu_client.ICUClient.update_event in-process via a
    # subprocess wrapper script (out of scope for this spec — adjust to
    # match File 05's actual seam name).

    result = subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "apply_adaptation.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--events", str(workspace["warehouse"] / "8_Events" / "events.json"),
         "--confirm"],
        capture_output=True, text=True, cwd=str(REPO_ICU),
        env={**__import__("os").environ, "ICU_DRY_RUN_PATCH": "1"},
    )
    assert result.returncode == 0, result.stderr
    entries = _read_ledger(workspace["ledger"])
    applied = [e for e in entries
               if e["decision_type"] == "adaptation_applied"]
    assert len(applied) >= 1


@pytest.mark.e2e
def test_full_chain_emits_all_eight_decision_types_and_one_suggestion(
        workspace: dict[str, Path], tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The grand-finale assertion: 8/8 decision_types + ≥1 suggestion."""
    target_date = "2026-04-28"

    # 1. Ingest
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "ingest_ledger.py"),
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )
    # 2. Adapt (red)
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "daily_adapt.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--ledger", str(workspace["ledger"])],
        check=True, cwd=str(REPO_ICU),
    )
    # 3. Consensus
    consensus_dir = tmp_path / "consensus_run"
    consensus_dir.mkdir(parents=True)
    response_md = (FIXTURE_ROOT / "consensus_response.md").read_text(
        encoding="utf-8")
    (consensus_dir / "council.response.md").write_text(response_md,
                                                       encoding="utf-8")
    athlete_state = tmp_path / "athlete_state.json"
    athlete_state.write_text(json.dumps({
        "ctl": 65.0, "atl": 67.0, "tsb": -2.0,
        "w_prime": 18000, "phase": "BUILD", "week_of_year": 17,
    }), encoding="utf-8")
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "finalize_consensus.py"),
         "--consensus-dir", str(consensus_dir),
         "--athlete-state", str(athlete_state),
         "--ledger", str(workspace["ledger"]),
         "--confirm"],
        check=True, cwd=str(REPO_ICU),
    )
    # 4. Apply adaptation
    monkeypatch.setenv("ICU_DRY_RUN_PATCH", "1")
    subprocess.run(
        [PYTHON, str(REPO_ICU / "scripts" / "apply_adaptation.py"),
         "--date", target_date,
         "--memory", str(workspace["memory"]),
         "--warehouse", str(workspace["warehouse"]),
         "--events", str(workspace["warehouse"] / "8_Events" / "events.json"),
         "--confirm"],
        check=True, cwd=str(REPO_ICU),
        env={**__import__("os").environ, "ICU_DRY_RUN_PATCH": "1"},
    )

    # 5. Verify all 8 decision types
    entries = _read_ledger(workspace["ledger"])
    types_seen = {e["decision_type"] for e in entries}
    expected_eight = {
        "phase_transition", "macro_plan_generated", "meso_block_created",
        "micro_cycle_generated", "weekly_plan_assembled",
        "adaptation_verdict", "consensus_verdict", "adaptation_applied",
    }
    assert expected_eight <= types_seen, (
        f"missing types: {expected_eight - types_seen}"
    )

    # 6. Replay suggester
    sys.path.insert(0, str(REPO_ICU))
    from src.coach.common.action_suggester import suggest_actions
    lines = suggest_actions(
        workspace["ledger"],
        workspace["memory"] / "periodization",
        workspace["memory"] / "deep_analysis",
        today=date.fromisoformat(target_date),
    )
    assert len(lines) >= 1, (
        "Suggester must emit at least one line; fixture seeded a "
        "phase_transition within the past 7 days (trigger #1)."
    )
```

### Step 2 — Run; expect failure

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/e2e/test_phase3_full_chain.py -v -m e2e
```

Expected error fragment:
```
FileNotFoundError: .../tests/fixtures/phase3/e2e/consensus_response.md
```

### Step 3 — Minimal implementation

There is **no source code** to implement for T71.2 — the entire deliverable
is fixture authoring (`consensus_response.md`) plus tuning the
`ICU_DRY_RUN_PATCH` environment variable to match File 05's actual seam
(verify by reading File 05's `apply_adaptation.py` once; if a different
seam is used — e.g. monkeypatch on `update_event` directly — adapt the
test accordingly without modifying File 05 source).

### Step 4 — Run; expect pass

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest \
    tests/e2e/test_phase3_full_chain.py -v -m e2e
```

Expected: 6 passed (2 from T71.1 + 4 from T71.2).

### Step 5 — Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add icu/tests/e2e/test_phase3_full_chain.py \
          icu/tests/fixtures/phase3/e2e/consensus_response.md && \
  git commit -m "test(coach-phase3): T71.2 e2e consensus→apply→suggester slice"
```

# Task 72 — Real-repo acceptance checklist (markdown only)

T72 has no code and runs no pytest. The deliverable is a markdown checklist
section authored INTO this spec file (below). After authoring, the only
action is a single commit. The checklist itself is meant to be executed by
the user (or a coach session) against `/mnt/d/Cycling/icu` after the
`ai-coach-phase-3` branch is merged onto a release branch (OQ4 lock).

## T72 — Step 1: Author checklist section verbatim

The full acceptance checklist follows. It is the deliverable.

## T72 — Step 2: Commit

```bash
cd /mnt/d/Cycling-phase3 && \
  git add docs/superpowers/plans/phase-3/09-integration-cli-tests.md && \
  git commit -m "docs(coach-phase3): T72 real-repo acceptance checklist"
```

(Only one file changes: this plan spec, with the checklist now authored.
No source / test files are touched.)

## T72 — Real-repo acceptance checklist

> **Run location:** `/mnt/d/Cycling/icu/` (the **main** repo, NOT the
> worktree at `/mnt/d/Cycling-phase3/`). Per OQ4 lock: this checklist runs
> only AFTER `ai-coach-phase-3` is merged into a release branch (typically
> `master`) and the user is back on the main repo.

> **Pre-flight:** `cd /mnt/d/Cycling/icu && git status` shows a clean tree
> on the merged-with-Phase-3 branch. `.venv/bin/python -c "from
> src.coach.common.action_suggester import suggest_actions"` exits 0
> (Phase 3 wired in).

### 0. Backup

- [ ] **0.1** Snapshot the current ledger and adapter dirs:
  ```bash
  cd /mnt/d/Cycling/icu
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  cp -r coach_memory/ledger      "/tmp/phase3_acceptance_${ts}/ledger"      2>/dev/null || mkdir -p "/tmp/phase3_acceptance_${ts}" && cp -r coach_memory/ledger      "/tmp/phase3_acceptance_${ts}/ledger"      2>/dev/null
  cp -r coach_memory/adapter     "/tmp/phase3_acceptance_${ts}/adapter"     2>/dev/null
  cp -r coach_memory/consensus   "/tmp/phase3_acceptance_${ts}/consensus"   2>/dev/null
  echo "snapshot at /tmp/phase3_acceptance_${ts}"
  ```
  **Expected:** prints a snapshot path; if any of the three dirs is
  absent (first-ever run), the cp errors are benign.

### 1. Full sync_data run with Phase 3 tail

- [ ] **1.1** Run the orchestrator end-to-end:
  ```bash
  cd /mnt/d/Cycling/icu && .venv/bin/python scripts/sync_data.py
  ```
  **Expected:**
  - Steps 1–10 print as before.
  - Step 11 line `======== ingest_ledger.py ========` appears; ingester
    prints per-decision-type counts.
  - Step 12 line `======== daily_adapt.py ========` appears; daily_adapt
    prints a JSON blob with `verdict` ∈ {green, yellow, red}.
  - Step 13: if any of the 4 triggers fires, the header
    `📌 Phase 3 建议` appears followed by indented bullets; otherwise
    nothing prints.
  - Final line `🎉 全量同步完成！` (green) OR
    `⚠️ 同步完成，但 N 个脚本失败:` (yellow). Phase 3 step failures
    must NOT cause exit non-zero.
  - Exit code 0 (`echo $?`).

- [ ] **1.2** Verify ledger appended:
  ```bash
  cd /mnt/d/Cycling/icu
  wc -l coach_memory/ledger/decisions.jsonl
  tail -n 1 coach_memory/ledger/decisions.jsonl | python3 -m json.tool
  ```
  **Expected:** line count > pre-step-1.1 count; tail entry is a valid
  JSON object whose `decision_type` is one of the 8 enum values.

- [ ] **1.3** Verify adapter outputs (if today is non-green):
  ```bash
  ls -la coach_memory/adapter/today_$(date +%F).md
  ls -la coach_memory/adapter/proposed_session_$(date +%F).json 2>/dev/null
  ```
  **Expected:** `today_<date>.md` exists when verdict ∈ {yellow, red};
  `proposed_session_<date>.json` exists only when verdict == red.

### 2. push_plan v2 (Phase 2 path; Phase 3 inert)

- [ ] **2.1** Generate next week's plan via Phase 2 v2 engine:
  ```bash
  cd /mnt/d/Cycling/icu && .venv/bin/python scripts/push_plan.py --engine v2
  ```
  **Expected:**
  - Plan file `coach_memory/reports/plan_<W>.json` written for next week.
  - Trace file `coach_memory/reports/plan_<W>.trace.json` written.
  - No ICU push (no `--push` flag).
  - Exit 0.

- [ ] **2.2** Confirm ledger gained a `weekly_plan_assembled` entry on the
  next sync:
  ```bash
  cd /mnt/d/Cycling/icu && .venv/bin/python scripts/sync_data.py
  grep -c '"decision_type":"weekly_plan_assembled"' \
      coach_memory/ledger/decisions.jsonl
  ```
  **Expected:** count incremented by exactly 1.

### 3. Opt-in run_consensus (council mode)

- [ ] **3.1** Build athlete_state JSON from current state:
  ```bash
  cd /mnt/d/Cycling/icu
  .venv/bin/python -c "
  import json
  w = json.loads(open('icu_data_warehouse/2_Wellness/wellness_history.json').read())[-1]
  cp = json.loads(open('coach_memory/physiology/cp_w_current.json').read())
  ph = json.loads(open('coach_memory/periodization/phase_current.json').read())
  from datetime import date
  print(json.dumps({
      'ctl': float(w['ctl']), 'atl': float(w['atl']),
      'tsb': float(w['ctl']) - float(w['atl']),
      'w_prime': int(cp['w_prime_joules']),
      'phase': ph.get('current_phase', 'BUILD'),
      'week_of_year': date.today().isocalendar()[1],
  }, indent=2))
  " > /tmp/athlete_state.json
  cat /tmp/athlete_state.json
  ```
  **Expected:** valid JSON with 6 fields, `ctl`/`atl` reflecting today.

- [ ] **3.2** Run consensus to emit prompt:
  ```bash
  cd /mnt/d/Cycling/icu
  W=$(date +%GW%V)   # ISO week, e.g. 2026W17
  .venv/bin/python scripts/run_consensus.py \
    --athlete-state /tmp/athlete_state.json \
    --plan coach_memory/reports/plan_${W}.json \
    --memory coach_memory \
    --out coach_memory/consensus/$(date -u +%Y-%m-%d_%H%M)
  ```
  **Expected:**
  - Directory `coach_memory/consensus/<TS>/` created.
  - File `council.prompt.md` exists, ≥200 lines, contains all 4 role tags
    (`<planner>`, `<critic>`, `<physiologist>`, `<arbiter>`).
  - Exit 0.

### 4. Manual Gemini paste

- [ ] **4.1** Open `coach_memory/consensus/<TS>/council.prompt.md` in
  the editor. Copy entire contents. Paste into Gemini Code Assist
  (or the Claude Code coach session). Receive reply.

- [ ] **4.2** Save the reply verbatim to
  `coach_memory/consensus/<TS>/council.response.md` (UTF-8). Do NOT
  trim, do NOT reformat.
  **Expected:** file exists; contains all 4 role tags + a
  `<summary_json>` block.

### 5. finalize_consensus

- [ ] **5.1** Append the verdict to the ledger:
  ```bash
  cd /mnt/d/Cycling/icu
  TS=<dir from step 3.2>
  .venv/bin/python scripts/finalize_consensus.py \
    --consensus-dir coach_memory/consensus/${TS} \
    --athlete-state /tmp/athlete_state.json \
    --ledger coach_memory/ledger/decisions.jsonl \
    --confirm
  ```
  **Expected:**
  - Stdout: `Appended consensus_verdict entry_id=01H...`
  - File `coach_memory/consensus/${TS}/verdict.md` written.
  - Re-running the same command (idempotency probe) prints
    `Already finalized: ...` and exit 0.
  - Ledger gained exactly 1 new `consensus_verdict` line.

- [ ] **5.2** If parser rejects (CRITIC_3_POINTS_MIN or
  PHYSIOLOGIST_QUANT_3_OF_4 violation):
  ```
  Expected: stderr lists each violated rule; exit code non-zero;
  ledger NOT modified.
  Action: re-edit council.response.md (or re-paste prompt to Gemini),
  re-run step 5.1.
  ```

### 6. Next-day daily_adapt + apply_adaptation (red path only)

- [ ] **6.1** Wait until tomorrow OR set `--date` to a known stressed
  recovery day for testing. Then:
  ```bash
  cd /mnt/d/Cycling/icu
  .venv/bin/python scripts/daily_adapt.py \
    --date $(date -u +%F) \
    --memory coach_memory \
    --warehouse icu_data_warehouse
  ```
  **Expected:** prints JSON `{verdict: <green|yellow|red>, ...}`. If red,
  `coach_memory/adapter/proposed_session_<date>.json` exists.

- [ ] **6.2** **ONLY IF** verdict == red AND user wants to override:
  ```bash
  cd /mnt/d/Cycling/icu
  # Dry-run first (default, no --confirm)
  .venv/bin/python scripts/apply_adaptation.py --date $(date +%F)
  # Inspect the printed PATCH payload carefully.
  # Apply for real:
  .venv/bin/python scripts/apply_adaptation.py --date $(date +%F) --confirm
  ```
  **Expected (dry-run):** JSON payload printed; reminder line `dry-run,
  append --confirm to apply`; ledger NOT modified.
  **Expected (--confirm):** stdout `applied event_id=...`; ledger gained
  exactly 1 new `adaptation_applied` line; on Intervals.icu calendar the
  workout for today shows the new title/description.

- [ ] **6.3** **IF** apply_adaptation fails (network error / 4xx):
  ```
  Expected: stderr prints the error; ledger NOT modified; calendar
  unchanged. Re-run after fix.
  ```

### 7. Manual ledger inspection

- [ ] **7.1** Verify all 8 decision types present:
  ```bash
  cd /mnt/d/Cycling/icu
  python3 -c "
  import json
  types = set()
  with open('coach_memory/ledger/decisions.jsonl', encoding='utf-8') as f:
      for line in f:
          if line.strip():
              types.add(json.loads(line)['decision_type'])
  expected = {'phase_transition','macro_plan_generated','meso_block_created',
              'micro_cycle_generated','weekly_plan_assembled',
              'adaptation_verdict','consensus_verdict','adaptation_applied'}
  print('present:', sorted(types))
  missing = expected - types
  print('missing:', sorted(missing))
  "
  ```
  **Expected:** `missing: []` (empty list). If any missing, trace back
  to the step that should have emitted it.

- [ ] **7.2** Verify chronological + ULID monotonic:
  ```bash
  python3 -c "
  import json
  prev_id, prev_ts = '', ''
  with open('coach_memory/ledger/decisions.jsonl', encoding='utf-8') as f:
      for n, line in enumerate(f, 1):
          if not line.strip(): continue
          e = json.loads(line)
          assert e['entry_id'] > prev_id, f'line {n}: ULID regression {e[\"entry_id\"]} <= {prev_id}'
          assert e['timestamp'] >= prev_ts, f'line {n}: timestamp regression'
          prev_id, prev_ts = e['entry_id'], e['timestamp']
  print('OK')
  "
  ```
  **Expected:** prints `OK`. APPEND_ONLY_LEDGER (decision lock #4)
  invariant verified.

- [ ] **7.3** Verify NO `superseded_by` populated unless explicitly
  authored (rare):
  ```bash
  grep -c '"superseded_by":"' coach_memory/ledger/decisions.jsonl || echo 0
  ```
  **Expected:** 0 unless the user has manually appended a correction
  entry.

### 8. Schema diff check (regression net)

- [ ] **8.1** Confirm `requirements.txt` unchanged (NO_NEW_DEPS):
  ```bash
  cd /mnt/d/Cycling/icu && git log -1 --pretty=%H requirements.txt
  ```
  **Expected:** SHA matches the pre-Phase-3 baseline (or the merge
  commit; no new lines added during Phase 3).

- [ ] **8.2** Confirm Phase 1/2 source files byte-identical to
  pre-merge tag (PHASE_1_2_IMMUTABILITY decision lock #2):
  ```bash
  cd /mnt/d/Cycling/icu
  for f in src/coach/physiology src/coach/deep_analyzer \
           src/coach/periodization src/coach/session_designer \
           scripts/refresh_physiology.py scripts/run_deep_analysis.py \
           scripts/update_coach_brief.py src/coach/phase1_injection.py \
           src/coach/brief_updater.py; do
      git diff <pre-phase-3-tag>..HEAD -- "$f" | head -1
  done
  ```
  **Expected:** every line is empty (no diff). Replace
  `<pre-phase-3-tag>` with the actual tag (e.g.
  `v2.0-phase2-complete`).

- [ ] **8.3** Confirm `sync_data.py` diff is APPEND-ONLY (the lone
  immutability allowance):
  ```bash
  cd /mnt/d/Cycling/icu
  git diff <pre-phase-3-tag>..HEAD -- scripts/sync_data.py | grep '^-[^-]'
  ```
  **Expected:** no output (no removed lines). Only `+` lines, located
  AFTER the existing step-10 block, BEFORE the `if failures:` block.

- [ ] **8.4** API-free grep across new Phase 3 files:
  ```bash
  cd /mnt/d/Cycling/icu
  ! grep -rnE 'google\.genai|^import requests|^from requests|^import httpx|^from httpx|^import aiohttp|^from aiohttp|^import urllib|^from urllib' \
      src/coach/ledger src/coach/adapter src/coach/consensus \
      src/coach/common/action_suggester.py
  ```
  **Expected:** exit 0 (no matches; the leading `!` inverts).

- [ ] **8.5** Tag the release if everything green:
  ```bash
  cd /mnt/d/Cycling/icu && git tag v3.0-phase3-m1-accepted
  ```
  **Expected:** tag created locally. (Push is the user's choice.)

### Acceptance summary

The acceptance run is **green** when ALL of:

- [ ] Steps 0–8 boxes checked.
- [ ] All 8 decision types present in `decisions.jsonl` (step 7.1).
- [ ] APPEND_ONLY_LEDGER invariant holds (step 7.2).
- [ ] PHASE_1_2_IMMUTABILITY holds (steps 8.2 + 8.3).
- [ ] NO_NEW_DEPS holds (step 8.1).
- [ ] API_FREE_WORKFLOW grep clean (step 8.4).
- [ ] HUMAN_GATE_ON_ICU_WRITE respected (apply_adaptation only ran
      with explicit `--confirm` in step 6.2).
- [ ] RED_NO_AUTO_ESCALATE respected (no automatic strict escalation
      observed; consensus run was user-initiated in step 3.2).

Failure of any of these halts release; investigate the offending step
and either fix the implementation or roll back the offending commit
(see Rollback section below).

## Acceptance criteria

1. **Pytest deltas:**
   - `test_action_suggester.py` = 16 passed (14 + 2).
   - `test_sync_data_phase3_integration.py` = 8 passed (4 + 4).
   - `test_phase3_full_chain.py` = 6 passed (2 + 4) — `pytest -m e2e`.
   - Net delta: **+30 unit tests + +6 e2e tests = +36 tests**.
2. **Commits (exact, in order):**
   1. `feat(coach-phase3): T69.1 action_suggester pure function + 4 trigger detectors`
   2. `feat(coach-phase3): T69.2 action_suggester print_suggestions formatter`
   3. `feat(coach-phase3): T70.1 sync_data steps 11-12 ingest + adapt`
   4. `feat(coach-phase3): T70.2 sync_data step 13 suggester import-soft`
   5. `test(coach-phase3): T71.1 e2e fixtures + ingester→adapt slice`
   6. `test(coach-phase3): T71.2 e2e consensus→apply→suggester slice`
   7. `docs(coach-phase3): T72 real-repo acceptance checklist`
3. **`git diff --stat`** = ONLY the Touch list paths.
4. **API-free grep** (run from worktree root):
   ```bash
   ! grep -rnE 'google\.genai|^import requests|^from requests|^import httpx|^from httpx|^import aiohttp|^from aiohttp|^import urllib|^from urllib' \
       icu/src/coach/common/action_suggester.py icu/scripts/sync_data.py \
       icu/tests/unit/coach/common/ icu/tests/unit/scripts/test_sync_data_phase3_integration.py \
       icu/tests/e2e/test_phase3_full_chain.py
   ```
   must exit 0.
5. **No new deps:** `icu/requirements.txt` unchanged (decision lock #8).
6. **Phase 1/2 sync regression** stays green at every File 09 commit:
   `cd icu && .venv/bin/pytest tests/unit/ -k 'not e2e'` shows the
   pre-File-09 pass count + 30 new unit tests.
7. **PHASE_1_2_IMMUTABILITY:** zero edits under
   `icu/src/coach/{physiology,deep_analyzer,periodization,session_designer,
   ledger,adapter,consensus}/`. Only `icu/scripts/sync_data.py` is edited
   under the immutability allowance, and the edit is APPEND-only.
8. **Branch `ai-coach-phase-3`** at every commit.

## Smoke test (manual, optional)

Beyond automated tests, the user may run the e2e flow against a fresh
tmp dir:

```bash
cd /mnt/d/Cycling-phase3/icu
# Use the e2e fixture as a synthetic coach_memory
TMP=$(mktemp -d)
cp -r tests/fixtures/phase3/e2e/coach_memory_seed "$TMP/coach_memory"
cp -r tests/fixtures/phase3/e2e/warehouse_seed    "$TMP/icu_data_warehouse"
mkdir -p "$TMP/coach_memory/ledger" "$TMP/coach_memory/adapter"

.venv/bin/python scripts/ingest_ledger.py \
    --memory "$TMP/coach_memory" --warehouse "$TMP/icu_data_warehouse"
.venv/bin/python scripts/daily_adapt.py --date 2026-04-28 \
    --memory "$TMP/coach_memory" --warehouse "$TMP/icu_data_warehouse"

# Suggester replay
.venv/bin/python -c "
from pathlib import Path
from datetime import date
import sys; sys.path.insert(0, '.')
from src.coach.common.action_suggester import suggest_actions, print_suggestions
out = suggest_actions(
    Path('$TMP/coach_memory/ledger/decisions.jsonl'),
    Path('$TMP/coach_memory/periodization'),
    Path('$TMP/coach_memory/deep_analysis'),
    today=date(2026, 4, 28),
)
print_suggestions(out, header='📌 Phase 3 建议（smoke）')
"
```

**Expected:** at least one bullet line printed (trigger #1 fires).

## Rollback

Revert in reverse order: T72 → T71.2 → T71.1 → T70.2 → T70.1 → T69.2 →
T69.1. After every revert run:

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest tests/unit/ -q
```

Phase 1/2 + Files 01–08 tests stay green. After the T70.1 + T70.2 revert,
`scripts/sync_data.py` returns byte-identical to its pre-Phase-3 form
(verify with `git diff <pre-tag>..HEAD -- icu/scripts/sync_data.py` →
empty).

## Open questions / blueprint resolutions

These were raised during File 09 spec drafting; each has a locked
decision recorded here so implementers don't reopen them.

### OQ1 — Does `action_suggester` read coach_memory or take paths as args?

**Decision (locked).** **Take paths as args** (not a single
`coach_memory` root). Rationale: testability — fixtures use `tmp_path`
and pass three independent paths so each trigger can be exercised in
isolation. The `sync_data.py` step-13 wrapper is responsible for
deriving `MEMORY_DIR / "ledger" / "decisions.jsonl"`,
`MEMORY_DIR / "periodization"`, `MEMORY_DIR / "deep_analysis"` from a
single `coach_memory` root.

### OQ2 — Should `sync_data.py` exit non-zero when a Phase 3 step fails?

**Decision (locked).** **NO** — soft-fail only. Per blueprint and
00-index.md execution rule #8, the new steps wrap any failure in
try/except and append to `failures` (or print warning for
ImportError). Phase 1 sync MUST NEVER turn red because Phase 3
exploded. Test
`test_main_exit_does_not_raise_when_phase3_step_fails` pins this.

### OQ3 — Where does the e2e fixture root live?

**Decision (locked).** `icu/tests/fixtures/phase3/e2e/`. Rationale:
sibling to existing `tests/fixtures/phase3/{adapter,consensus,...}`
trees. Sub-trees `coach_memory_seed/` and `warehouse_seed/` mirror the
real folder names so the test can `shutil.copytree(...)` directly.
Single Gemini fixture `consensus_response.md` lives at the root of the
e2e fixture dir.

### OQ4 — Does T72 checklist run in worktree or main `/mnt/d/Cycling/icu`?

**Decision (locked).** **Main repo** `/mnt/d/Cycling/icu/`, AFTER
`ai-coach-phase-3` is merged into a release branch. Rationale: T72 is
the real-repo acceptance gate; running it inside the worktree would
exercise the wrong `coach_memory` (the worktree's `coach_memory` is
likely a synthetic copy). The checklist explicitly cites this in its
**Run location** preamble so the user does not run it in the wrong
directory.

### OQ5 — What if File 05's mock ICU PATCH seam isn't `ICU_DRY_RUN_PATCH` env?

**Decision (locked).** Adapt T71.2's `apply_adaptation` test to whatever
seam File 05 actually exposes (read `tests/fixtures/phase3/adapter/`
once; read `scripts/apply_adaptation.py` once). Acceptable seams:
(a) env var `ICU_DRY_RUN_PATCH=1`; (b) monkeypatch on
`src.fetcher.icu_client.ICUClient.update_event` (in-process, requires
running apply_adaptation as in-process import rather than subprocess);
(c) running an HTTP mock server on a random port and pointing
`ICU_BASE_URL` at it. Pick the same seam already used by File 05's
own apply_adaptation tests; do NOT invent a new one. Implementer must
update the test code shown in T71.2 step 1 accordingly without
modifying File 05 source.

### OQ6 — Does T71 e2e count toward the 80% coverage gate?

**Decision (locked).** **NO.** E2e tests run under `pytest -m e2e` and
are excluded from the unit-coverage tally. The 80% coverage rule (per
~/.claude/rules/common/testing.md) is satisfied by the unit tests in
File 09 (T69 + T70) plus the entire Phase 3 unit suite from Files
01–08. E2e tests are a smoke gate; coverage credit goes to the unit
counterparts.

### OQ7 — Should the suggester ever short-circuit (skip later triggers)?

**Decision (locked).** **NO.** All 4 triggers always run; each is
independent. The output list is the union (in stable order). Rationale:
the user values seeing all advisory signals at once over performance
(blueprint "触发方式" enumerates triggers as a flat list, not a
priority chain).

## End-of-file checkpoint

- [ ] All 7 commits landed on `ai-coach-phase-3` in the locked order.
- [ ] `cd icu && .venv/bin/pytest tests/unit/coach/common/
      tests/unit/scripts/test_sync_data_phase3_integration.py` green.
- [ ] `cd icu && .venv/bin/pytest tests/e2e/test_phase3_full_chain.py
      -m e2e` green; +6 e2e tests.
- [ ] Net pytest delta vs pre-File-09 baseline: **+~30 unit tests +
      ~6 e2e tests**.
- [ ] API-free grep returns exit 0 (no match) on the 5 listed paths.
- [ ] `git diff --stat` shows ONLY the Touch list paths.
- [ ] T72 real-repo acceptance checklist authored in this file (this
      whole "## T72 — Real-repo acceptance checklist" section verbatim
      committed with `docs(coach-phase3): T72 real-repo acceptance
      checklist`).
- [ ] `save-progress` run; MEMORY.md update deferred to parent session.
- [ ] Next session = NONE for File 09 itself. After File 09 is merged
      back to master, the user runs the T72 checklist against
      `/mnt/d/Cycling/icu/` and tags `v3.0-phase3-m1-accepted` on
      success.

## Worktree bootstrap reminder

In a fresh worktree, untracked `icu/src/{analyzer,utils,fetcher}` +
`icu/.venv/` are missing (per user-memory `worktree_setup_icu.md`).
Bootstrap with:

```bash
cp -r /mnt/d/Cycling/icu/src/{analyzer,utils,fetcher} \
      /mnt/d/Cycling-phase3/icu/src/
ln -s /mnt/d/Cycling/icu/.venv /mnt/d/Cycling-phase3/icu/.venv
```

Verify Files 01–08 baseline green BEFORE starting File 09:

```bash
cd /mnt/d/Cycling-phase3/icu && .venv/bin/pytest tests/unit/ -q
```

Should match the post-File-08 baseline (683 unit tests + File 08's +65
= 748 unit tests). If lower, do NOT proceed — debug worktree setup
first.

## Subagent brief

> Use `docs/superpowers/plans/phase-3/09-integration-cli-tests.md`. Apply
> `superpowers:subagent-driven-development`. Execute T69.1 → T69.2 →
> T70.1 → T70.2 → T71.1 → T71.2 → T72. Each TDD task: RED test + fail →
> minimal impl → pass → commit. T72 has only Step 1 (author the
> checklist verbatim — already authored in the spec) + Step 2 (commit).
>
> Apply the 9-item Pre-flight Pydantic+IO checklist (especially item 1:
> File 09 adds NO Pydantic models — `suggest_actions` returns
> `list[str]`).
>
> Honour the touch list — no edits under `src/coach/{physiology,
> deep_analyzer,periodization,session_designer,ledger,adapter,
> consensus}/`. The ONLY allowed edit outside the new Phase 3 files is
> `icu/scripts/sync_data.py`, and the edit MUST be APPEND-only between
> existing lines 66 and 68 — invoke the PHASE_1_2_IMMUTABILITY
> allowance per 00-index.md decision lock #2.
>
> No new requirements.txt entries (NO_NEW_DEPS, lock #8). No
> `import google.genai|requests|httpx|urllib|aiohttp` in any new file.
>
> Phase 1/2 unit + Files 01–08 unit regression must stay green after
> EVERY commit. After T70.1 (the first sync_data edit), explicitly
> re-run `cd icu && .venv/bin/pytest tests/unit/ -q` and report the
> count.
>
> For T71 e2e: invoke real Phase 3 CLIs via `subprocess.run` against
> `tmp_path`; mock ICU PATCH using whatever seam File 05 already
> exposes (do NOT modify File 05 to add a new seam — see OQ5). If the
> seam is unclear, read `scripts/apply_adaptation.py` once and adapt
> the test code shown in T71.2 Step 1 accordingly.
>
> Report: 7 task IDs, file paths, pytest deltas (unit + e2e
> separately), deviations.

## Glossary

- **action_suggester** — Phase 3 advisory hook that emits
  human-readable lines based on 4 trigger conditions; never executes
  commands.
- **trigger condition** — boolean predicate evaluated against the
  ledger or deep_analysis snapshots; emits at most one advisory line.
- **soft-fail** — try/except wrapper that turns subprocess /
  ImportError / arbitrary `Exception` into a warning print + (for the
  third) a `failures.append(...)` — never propagates.
- **immutability allowance** — the ONE permitted Phase 3 edit to
  Phase 1/2 surface area: appending steps 11–13 to `sync_data.py`
  between line 66 and line 68.
- **e2e fixture root** — `icu/tests/fixtures/phase3/e2e/`, sibling to
  the per-component `phase3/{adapter,consensus,...}` dirs.
- **ICU_DRY_RUN_PATCH** — illustrative env-var seam name; the actual
  seam is whatever File 05's mock test already uses (OQ5).
- **frozen Gemini reply** — `consensus_response.md` fixture authored
  by hand, satisfying File 06's parser hard rules; shipped under
  `tests/fixtures/phase3/e2e/`.
- **8/8 decision_types** — the 8 enum values in `DecisionType`
  literal: `phase_transition`, `macro_plan_generated`,
  `meso_block_created`, `micro_cycle_generated`,
  `weekly_plan_assembled`, `consensus_verdict`, `adaptation_verdict`,
  `adaptation_applied`. The grand-finale e2e test pins all 8.
- **CONSENSUS_OVERDUE_DAYS** — module constant in `action_suggester.py`,
  fixed at 14 (matches blueprint "触发方式" trigger #3).
- **STIMULUS_DECLINE_WINDOW** — module constant in
  `action_suggester.py`, fixed at 3.
