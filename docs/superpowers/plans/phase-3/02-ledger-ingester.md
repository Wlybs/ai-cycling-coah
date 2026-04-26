# Phase 3 — Ledger ingester (Tasks T53–T54)

> Part of the Phase 3 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Goal:** 交付 `Ingester` 一次性扫 Phase 2 产物回补 Ledger 的能力，守住 "不改 Phase 1/2" 约束 —— Phase 2 侧只负责写它自己的 JSON / trace 文件，Ingester 读这些文件并用 `LedgerWriter` 补写对应的 `DecisionEntry`。同时交付 `scripts/ingest_ledger.py` CLI 供独立调用（sync_data.py 集成留给 File 09）。

**Files covered:**
- `icu/src/coach/ledger/ingester.py`
- `icu/scripts/ingest_ledger.py`
- `icu/tests/unit/ledger/test_ingester.py`
- `icu/tests/unit/ledger/test_ingest_ledger_cli.py`

**Hard constraints (from 00-index.md):**
- `PHASE_1_2_IMMUTABILITY`: Ingester **只读** Phase 1/2 已写的 JSON；不 import 任何 `src.coach.periodization.*` / `src.coach.session_designer.*` 类型做反序列化校验（让 Ingester 对 Phase 2 schema 微调免疫）。
- `APPEND_ONLY_LEDGER`: 只经 `LedgerWriter.record()` 追加；幂等性通过查 ledger 历史判断 "已写过吗"，而不是改已有行。
- `NO_NEW_DEPS`: 仅 stdlib + Pydantic v2 + 已交付的 `src.coach.ledger.*`。
- `API_FREE_WORKFLOW`: 不 import `google.genai` / 任何 LLM SDK。
- **Dependency:** 本文件假定 File 01 (T50–T52) 已合并；`LedgerWriter` / `LedgerReader` / `DecisionEntry` / `AthleteStateRef` 已可 import。

**Payload 摘取规则（硬合同 — 蓝图 §4.4）：**

| decision_type | 数据来源 | payload 字段 | 幂等键 |
|---|---|---|---|
| `phase_transition` | `periodization/phase_current.json` | `from_phase`（上一条 entry 的 `to_phase`，首次为 `null`）、`to_phase`、`trigger_rules`、`ctl_slope_14d`、`override_applied` | 最新 `phase_transition` entry 的 `to_phase` ≠ 文件 `phase` → 写 |
| `macro_plan_generated` | `periodization/macro_plan.json` | `season_end_date`、`windows_count`、`phase_sequence`、`generated_at` | 文件 `generated_at` 与任何历史 entry `payload.generated_at` 不同 → 写 |
| `meso_block_created` | `periodization/meso_block.json` | `pattern`、`block_start`、`block_end`、`weeks`、`phase` | `(block_start, block_end)` 未在历史 entry 中出现 → 写 |
| `micro_cycle_generated` | `periodization/micro_cycle_*.json`（glob） | `week_start`、`hard_days`、`tss_target`、`phase` | `week_start` ISO 日期串未在历史 entry 中出现 → 写 |
| `weekly_plan_assembled` | `reports/plan_*.trace.json` + 对应 `plan_*.json` | `plan_date`、`total_tss`、`sessions_by_type`、`trace_refs` | trace 文件名未在历史 entry 的 `trace_refs` 中出现 → 写（trace 缺失 → 跳过 plan） |

---

## Task 53: Ingester — idempotent scan of Phase 2 artifacts

**Files:**
- Create: `icu/src/coach/ledger/ingester.py`
- Create: `icu/tests/unit/ledger/test_ingester.py`

**Design notes:**
- **Defensive read.** 所有 Phase 2 输入统一走 `json.loads` + `.get(...)` 容错；文件缺失或 JSON 破损直接返回 `None` 并记 `ledger_ingest_skip_malformed` 事件，不抛异常。
- **Dependency injection.** `Ingester.__init__` 接收 `writer` 与 `athlete_state` 两个依赖：写入路径由 caller 决定（让测试用 tmp_path），`athlete_state` 作为本次 ingestion run 所有 entry 共享的 state snapshot（回补即 "承认这批 Phase 2 决策是以当前状态为背景做出的"；完全实时的 state 记录走 Phase 3 的 consensus / adapter 实时写入）。
- **Hard-days 规则.** Micro cycle 里 `tier` 属于 `{"REST","RECOVERY","ENDURANCE","TEMPO"}` 视为非硬性；其余（`SWEET_SPOT`/`THRESHOLD`/`VO2MAX`/`ANAEROBIC`/`NEUROMUSCULAR` 等）全部计入 `hard_days`。用 **排除型** 白名单，方便 Phase 2 新增 tier 枚举值时自动纳入（遵守 `PHASE_1_2_IMMUTABILITY` 的精神）。
- **Counts contract.** `run()` 返回固定 5 个键的 dict，`dry_run=True` 时计算写入 *会* 发生的次数但不实际写；测试既查 dict 又查 ledger 行数双保险。
- **Order.** 5 个 decision_type 串行执行。每一步调用 `LedgerReader.query(...)` 重新扫 ledger，所以上一步写入的 entry 对下一步可见（不自嵌套，不抛 cache 问题）。

- [ ] **Step 1: Write failing tests — idempotency + payload correctness per decision_type**

Write `icu/tests/unit/ledger/test_ingester.py`:
```python
"""Unit tests for Ingester: scans Phase 2 artifacts, writes DecisionEntries idempotently."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.coach.ledger.ingester import Ingester
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter


# ---------- helpers ----------

def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_state() -> AthleteStateRef:
    return AthleteStateRef(
        ctl=72.3, atl=85.1, tsb=-12.8,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )


@pytest.fixture
def memory_root(tmp_path: Path) -> Path:
    """Emulates `coach_memory/` layout with ledger/, periodization/, reports/ subdirs."""
    (tmp_path / "ledger").mkdir()
    (tmp_path / "periodization").mkdir()
    (tmp_path / "reports").mkdir()
    return tmp_path


def _make_ingester(memory_root: Path, state: AthleteStateRef | None = None) -> Ingester:
    writer = LedgerWriter(memory_root / "ledger" / "decisions.jsonl")
    return Ingester(
        memory_root=memory_root,
        writer=writer,
        athlete_state=state or _default_state(),
    )


def _entries(memory_root: Path, decision_type: str | None = None):
    reader = LedgerReader(memory_root / "ledger" / "decisions.jsonl")
    return reader.query(decision_type=decision_type)


def _micro_cycle_doc(week_start: str, tss: int, phase: str = "BUILD") -> dict:
    return {
        "week_start": week_start,
        "week_end": "2026-04-19",
        "phase": phase,
        "weekly_tss_target": tss,
        "days": [
            {"day_of_week": "Mon", "tier": "REST", "target_tss": 0, "session_hint": "off"},
            {"day_of_week": "Tue", "tier": "THRESHOLD", "target_tss": 90, "session_hint": "2x20"},
            {"day_of_week": "Wed", "tier": "ENDURANCE", "target_tss": 60, "session_hint": "z2"},
            {"day_of_week": "Thu", "tier": "VO2MAX", "target_tss": 85, "session_hint": "5x4"},
            {"day_of_week": "Fri", "tier": "RECOVERY", "target_tss": 30, "session_hint": "z1"},
            {"day_of_week": "Sat", "tier": "SWEET_SPOT", "target_tss": 120, "session_hint": "4x15"},
            {"day_of_week": "Sun", "tier": "ENDURANCE", "target_tss": 95, "session_hint": "z2 long"},
        ],
    }


def _weekly_plan_doc(week_start: str, tss: int = 480) -> dict:
    return {
        "week_start": week_start,
        "week_end": "2026-04-19",
        "focus_theme": "build threshold",
        "weekly_tss_target": tss,
        "coaching_summary": "test",
        "days": [
            {"date": week_start, "day_of_week": "Mon", "training_type": "REST",
             "icu_type": "Rest", "name": "off", "description": "",
             "duration_min": 0, "target_tss": 0},
            {"date": week_start, "day_of_week": "Tue", "training_type": "THRESHOLD",
             "icu_type": "Ride", "name": "2x20", "description": "",
             "duration_min": 90, "target_tss": 95},
            {"date": week_start, "day_of_week": "Wed", "training_type": "ENDURANCE",
             "icu_type": "Ride", "name": "z2", "description": "",
             "duration_min": 120, "target_tss": 65},
        ],
    }


def _trace_doc() -> dict:
    return {"composer_version": "1.0", "violations": [], "templates_used": ["threshold_2x20"]}


# ---------- phase_transition ----------

def test_phase_transition_writes_when_no_prior_entry(memory_root):
    _write_json(memory_root / "periodization" / "phase_current.json", {
        "phase": "BUILD",
        "transition_reasons": ["ctl_slope_above_threshold"],
        "ctl_slope_14d": 0.62,
        "override_applied": False,
    })
    counts = _make_ingester(memory_root).run()
    assert counts["phase_transition"] == 1

    entries = _entries(memory_root, "phase_transition")
    assert len(entries) == 1
    p = entries[0].payload
    assert p["to_phase"] == "BUILD"
    assert p["from_phase"] is None
    assert p["trigger_rules"] == ["ctl_slope_above_threshold"]
    assert p["ctl_slope_14d"] == 0.62
    assert p["override_applied"] is False


def test_phase_transition_is_idempotent_on_same_phase(memory_root):
    _write_json(memory_root / "periodization" / "phase_current.json", {
        "phase": "BUILD",
        "transition_reasons": ["x"],
    })
    ing = _make_ingester(memory_root)
    ing.run()
    counts2 = ing.run()
    assert counts2["phase_transition"] == 0
    assert len(_entries(memory_root, "phase_transition")) == 1


def test_phase_transition_appends_when_phase_changes(memory_root):
    pc = memory_root / "periodization" / "phase_current.json"
    _write_json(pc, {"phase": "BUILD", "transition_reasons": ["a"]})
    ing = _make_ingester(memory_root)
    ing.run()
    _write_json(pc, {"phase": "PEAK", "transition_reasons": ["b"]})
    ing.run()
    entries = _entries(memory_root, "phase_transition")
    assert len(entries) == 2
    assert entries[-1].payload["from_phase"] == "BUILD"
    assert entries[-1].payload["to_phase"] == "PEAK"


def test_phase_transition_skipped_when_file_missing(memory_root):
    counts = _make_ingester(memory_root).run()
    assert counts["phase_transition"] == 0
    assert _entries(memory_root, "phase_transition") == []


def test_phase_transition_handles_missing_optional_fields(memory_root):
    _write_json(memory_root / "periodization" / "phase_current.json", {"phase": "BASE"})
    _make_ingester(memory_root).run()
    entries = _entries(memory_root, "phase_transition")
    assert len(entries) == 1
    p = entries[0].payload
    assert p["to_phase"] == "BASE"
    assert p["ctl_slope_14d"] is None
    assert p["override_applied"] is False
    assert p["trigger_rules"] == []


# ---------- macro_plan_generated ----------

def test_macro_plan_writes_once_per_generated_at(memory_root):
    _write_json(memory_root / "periodization" / "macro_plan.json", {
        "generated_at": "2026-04-10T12:00:00+00:00",
        "season_end_date": "2026-09-30",
        "windows": [
            {"phase": "BASE"}, {"phase": "BUILD"}, {"phase": "PEAK"},
        ],
    })
    ing = _make_ingester(memory_root)
    ing.run()
    ing.run()
    entries = _entries(memory_root, "macro_plan_generated")
    assert len(entries) == 1
    p = entries[0].payload
    assert p["season_end_date"] == "2026-09-30"
    assert p["windows_count"] == 3
    assert p["phase_sequence"] == ["BASE", "BUILD", "PEAK"]
    assert p["generated_at"] == "2026-04-10T12:00:00+00:00"


def test_macro_plan_appends_when_generated_at_changes(memory_root):
    mp = memory_root / "periodization" / "macro_plan.json"
    _write_json(mp, {"generated_at": "2026-04-10T12:00:00+00:00",
                     "season_end_date": "2026-09-30", "windows": []})
    _make_ingester(memory_root).run()
    _write_json(mp, {"generated_at": "2026-04-20T12:00:00+00:00",
                     "season_end_date": "2026-10-15", "windows": []})
    _make_ingester(memory_root).run()
    entries = _entries(memory_root, "macro_plan_generated")
    assert len(entries) == 2
    assert entries[-1].payload["generated_at"] == "2026-04-20T12:00:00+00:00"


def test_macro_plan_skipped_when_file_missing(memory_root):
    counts = _make_ingester(memory_root).run()
    assert counts["macro_plan_generated"] == 0


# ---------- meso_block_created ----------

def test_meso_block_writes_once_per_block_range(memory_root):
    _write_json(memory_root / "periodization" / "meso_block.json", {
        "pattern": "3:1",
        "block_start": "2026-04-06",
        "block_end": "2026-05-03",
        "phase": "BUILD",
        "weekly_load_multipliers": [1.0, 1.05, 1.1, 0.7],
    })
    ing = _make_ingester(memory_root)
    ing.run()
    ing.run()
    entries = _entries(memory_root, "meso_block_created")
    assert len(entries) == 1
    p = entries[0].payload
    assert p["pattern"] == "3:1"
    assert p["block_start"] == "2026-04-06"
    assert p["block_end"] == "2026-05-03"
    assert p["weeks"] == 4
    assert p["phase"] == "BUILD"


def test_meso_block_appends_when_new_block(memory_root):
    mb = memory_root / "periodization" / "meso_block.json"
    _write_json(mb, {"pattern": "3:1", "block_start": "2026-04-06",
                     "block_end": "2026-05-03", "phase": "BUILD",
                     "weekly_load_multipliers": [1.0, 1.05, 1.1, 0.7]})
    _make_ingester(memory_root).run()
    _write_json(mb, {"pattern": "2:1", "block_start": "2026-05-04",
                     "block_end": "2026-05-24", "phase": "BUILD",
                     "weekly_load_multipliers": [1.0, 1.1, 0.7]})
    _make_ingester(memory_root).run()
    entries = _entries(memory_root, "meso_block_created")
    assert len(entries) == 2


# ---------- micro_cycle_generated ----------

def test_micro_cycle_derives_hard_days_and_payload(memory_root):
    _write_json(memory_root / "periodization" / "micro_cycle_2026W16.json",
                _micro_cycle_doc("2026-04-13", 480))
    _make_ingester(memory_root).run()
    entries = _entries(memory_root, "micro_cycle_generated")
    assert len(entries) == 1
    p = entries[0].payload
    assert p["week_start"] == "2026-04-13"
    assert p["tss_target"] == 480
    assert p["phase"] == "BUILD"
    # THRESHOLD + VO2MAX + SWEET_SPOT = 3 hard (REST/ENDURANCE/RECOVERY excluded)
    assert p["hard_days"] == 3


def test_micro_cycle_idempotent_by_week_start(memory_root):
    _write_json(memory_root / "periodization" / "micro_cycle_2026W16.json",
                _micro_cycle_doc("2026-04-13", 480))
    ing = _make_ingester(memory_root)
    ing.run()
    ing.run()
    assert len(_entries(memory_root, "micro_cycle_generated")) == 1


def test_micro_cycle_writes_multiple_weeks(memory_root):
    _write_json(memory_root / "periodization" / "micro_cycle_2026W16.json",
                _micro_cycle_doc("2026-04-13", 480))
    _write_json(memory_root / "periodization" / "micro_cycle_2026W17.json",
                _micro_cycle_doc("2026-04-20", 500))
    _make_ingester(memory_root).run()
    weeks = {e.payload["week_start"] for e in _entries(memory_root, "micro_cycle_generated")}
    assert weeks == {"2026-04-13", "2026-04-20"}


def test_micro_cycle_skipped_when_directory_empty(memory_root):
    counts = _make_ingester(memory_root).run()
    assert counts["micro_cycle_generated"] == 0


# ---------- weekly_plan_assembled ----------

def test_weekly_plan_reads_trace_and_json(memory_root):
    tag = "20260413"
    reports = memory_root / "reports"
    _write_json(reports / f"plan_{tag}.json", _weekly_plan_doc("2026-04-13"))
    _write_json(reports / f"plan_{tag}.trace.json", _trace_doc())
    _make_ingester(memory_root).run()
    entries = _entries(memory_root, "weekly_plan_assembled")
    assert len(entries) == 1
    p = entries[0].payload
    assert p["plan_date"] == "2026-04-13"
    assert p["total_tss"] == 480
    assert p["sessions_by_type"] == {"THRESHOLD": 1, "ENDURANCE": 1}  # REST filtered
    assert any("plan_20260413.trace.json" in r for r in p["trace_refs"])


def test_weekly_plan_idempotent_by_trace_file(memory_root):
    tag = "20260413"
    _write_json(memory_root / "reports" / f"plan_{tag}.json", _weekly_plan_doc("2026-04-13"))
    _write_json(memory_root / "reports" / f"plan_{tag}.trace.json", _trace_doc())
    ing = _make_ingester(memory_root)
    ing.run()
    ing.run()
    assert len(_entries(memory_root, "weekly_plan_assembled")) == 1


def test_weekly_plan_skips_when_trace_missing(memory_root):
    # plan_*.json exists but no trace → keyed on trace, so skip
    _write_json(memory_root / "reports" / "plan_20260420.json", _weekly_plan_doc("2026-04-20"))
    counts = _make_ingester(memory_root).run()
    assert counts["weekly_plan_assembled"] == 0
    assert _entries(memory_root, "weekly_plan_assembled") == []


def test_weekly_plan_appends_for_multiple_tags(memory_root):
    for tag, date_str in (("20260413", "2026-04-13"), ("20260420", "2026-04-20")):
        _write_json(memory_root / "reports" / f"plan_{tag}.json", _weekly_plan_doc(date_str))
        _write_json(memory_root / "reports" / f"plan_{tag}.trace.json", _trace_doc())
    _make_ingester(memory_root).run()
    assert len(_entries(memory_root, "weekly_plan_assembled")) == 2


# ---------- full run ----------

def test_run_writes_all_decision_types_once_then_idempotent(memory_root):
    _write_json(memory_root / "periodization" / "phase_current.json",
                {"phase": "BUILD", "transition_reasons": ["x"]})
    _write_json(memory_root / "periodization" / "macro_plan.json",
                {"generated_at": "2026-04-10T12:00:00+00:00",
                 "season_end_date": "2026-09-30",
                 "windows": [{"phase": "BASE"}, {"phase": "BUILD"}]})
    _write_json(memory_root / "periodization" / "meso_block.json",
                {"pattern": "3:1", "block_start": "2026-04-06",
                 "block_end": "2026-05-03", "phase": "BUILD",
                 "weekly_load_multipliers": [1.0, 1.05, 1.1, 0.7]})
    _write_json(memory_root / "periodization" / "micro_cycle_2026W16.json",
                _micro_cycle_doc("2026-04-13", 480))
    _write_json(memory_root / "reports" / "plan_20260413.json",
                _weekly_plan_doc("2026-04-13"))
    _write_json(memory_root / "reports" / "plan_20260413.trace.json", _trace_doc())

    ing = _make_ingester(memory_root)
    counts = ing.run()
    assert counts == {
        "phase_transition": 1,
        "macro_plan_generated": 1,
        "meso_block_created": 1,
        "micro_cycle_generated": 1,
        "weekly_plan_assembled": 1,
    }
    counts2 = ing.run()
    assert sum(counts2.values()) == 0


def test_run_returns_zero_counts_for_empty_memory_root(memory_root):
    counts = _make_ingester(memory_root).run()
    assert counts == {
        "phase_transition": 0,
        "macro_plan_generated": 0,
        "meso_block_created": 0,
        "micro_cycle_generated": 0,
        "weekly_plan_assembled": 0,
    }
    assert not (memory_root / "ledger" / "decisions.jsonl").exists()


def test_run_tolerates_corrupt_json_file(memory_root):
    # phase_current.json is malformed → skip, do not crash the run
    (memory_root / "periodization" / "phase_current.json").write_text(
        "NOT_JSON {", encoding="utf-8"
    )
    counts = _make_ingester(memory_root).run()
    assert counts["phase_transition"] == 0


# ---------- dry-run ----------

def test_dry_run_counts_without_writing(memory_root):
    _write_json(memory_root / "periodization" / "phase_current.json",
                {"phase": "BUILD", "transition_reasons": ["x"]})
    _write_json(memory_root / "periodization" / "micro_cycle_2026W16.json",
                _micro_cycle_doc("2026-04-13", 480))

    counts = _make_ingester(memory_root).run(dry_run=True)
    assert counts["phase_transition"] == 1
    assert counts["micro_cycle_generated"] == 1
    assert not (memory_root / "ledger" / "decisions.jsonl").exists()


def test_dry_run_then_real_run_writes_same_count(memory_root):
    _write_json(memory_root / "periodization" / "phase_current.json",
                {"phase": "BUILD", "transition_reasons": ["x"]})
    ing = _make_ingester(memory_root)
    dry = ing.run(dry_run=True)
    real = ing.run(dry_run=False)
    assert dry == real
    assert len(_entries(memory_root)) == 1
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_ingester.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.coach.ledger.ingester'`.

- [ ] **Step 3: Implement Ingester**

Write `icu/src/coach/ledger/ingester.py`:
```python
"""Ingester — 扫 Phase 2 产物回补 Ledger entries。

设计原则（见 docs/superpowers/plans/phase-3/02-ledger-ingester.md Design notes）：
1. 不反序列化成 Phase 2 Pydantic 模型 — 直接读 JSON dict + `.get()` 容错。
2. 幂等键按 decision_type 定义（见同文件 Payload 摘取规则表）。
3. 文件缺失 / JSON 破损 → 静默跳过 + log event。绝不抛异常阻塞整个 run。
4. 所有写入经 `LedgerWriter.record()` — 守 APPEND_ONLY 不变量。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.coach.common.logging import get_logger

from .reader import LedgerReader
from .types import AthleteStateRef
from .writer import LedgerWriter

_log = get_logger("ledger")

# Tiers that do NOT count as "hard day". Anything else (SWEET_SPOT,
# THRESHOLD, VO2MAX, ANAEROBIC, NEUROMUSCULAR, etc.) contributes to hard_days.
_SOFT_TIERS: frozenset[str] = frozenset({"REST", "RECOVERY", "ENDURANCE", "TEMPO"})

# Training types excluded from sessions_by_type counter (on WeeklyPlan days).
_NON_SESSION_TYPES: frozenset[str] = frozenset({"REST"})


class Ingester:
    """一次性扫 Phase 2 artifacts 并追加 5 种 decision_type 的 ledger entry。"""

    def __init__(
        self,
        *,
        memory_root: Path,
        writer: LedgerWriter,
        athlete_state: AthleteStateRef,
    ) -> None:
        self.memory_root = Path(memory_root)
        self.writer = writer
        self.athlete_state = athlete_state
        self._reader = LedgerReader(writer.path)

    # ---------- public ----------

    def run(self, *, dry_run: bool = False) -> dict[str, int]:
        """Scan artifacts in order; return per-decision_type write count."""
        counts: dict[str, int] = {
            "phase_transition": self._ingest_phase(dry_run),
            "macro_plan_generated": self._ingest_macro(dry_run),
            "meso_block_created": self._ingest_meso(dry_run),
            "micro_cycle_generated": self._ingest_micro(dry_run),
            "weekly_plan_assembled": self._ingest_weekly_plans(dry_run),
        }
        _log.event(
            "ledger_ingest_done",
            dry_run=dry_run,
            total=sum(counts.values()),
            **{f"n_{k}": v for k, v in counts.items()},
        )
        return counts

    # ---------- shared ----------

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.event("ledger_ingest_skip_malformed",
                       path=str(path), reason=str(exc))
            return None
        return data if isinstance(data, dict) else None

    def _emit(
        self,
        *,
        decision_type: str,
        source: str,
        payload: dict[str, Any],
        evidence_refs: list[str] | None,
        dry_run: bool,
    ) -> int:
        if dry_run:
            return 1
        self.writer.record(
            decision_type=decision_type,  # type: ignore[arg-type]
            source=source,
            athlete_state=self.athlete_state,
            payload=payload,
            evidence_refs=evidence_refs or [],
        )
        return 1

    # ---------- phase_transition ----------

    def _ingest_phase(self, dry_run: bool) -> int:
        data = self._read_json(self.memory_root / "periodization" / "phase_current.json")
        if data is None:
            return 0
        to_phase = data.get("phase")
        if not to_phase:
            return 0

        prior = self._reader.query(decision_type="phase_transition", limit=1)
        last_to = prior[-1].payload.get("to_phase") if prior else None
        if last_to == to_phase:
            return 0

        payload = {
            "from_phase": last_to,
            "to_phase": to_phase,
            "trigger_rules": list(data.get("transition_reasons") or []),
            "ctl_slope_14d": data.get("ctl_slope_14d"),
            "override_applied": bool(data.get("override_applied", False)),
        }
        return self._emit(
            decision_type="phase_transition",
            source="ingester.phase_detector",
            payload=payload,
            evidence_refs=["periodization/phase_current.json"],
            dry_run=dry_run,
        )

    # ---------- macro_plan_generated ----------

    def _ingest_macro(self, dry_run: bool) -> int:
        data = self._read_json(self.memory_root / "periodization" / "macro_plan.json")
        if data is None:
            return 0
        gen_at = data.get("generated_at")
        if not gen_at:
            return 0

        prior = self._reader.query(decision_type="macro_plan_generated")
        if any(e.payload.get("generated_at") == gen_at for e in prior):
            return 0

        windows = list(data.get("windows") or [])
        payload = {
            "season_end_date": data.get("season_end_date"),
            "windows_count": len(windows),
            "phase_sequence": [w.get("phase") for w in windows if isinstance(w, dict) and w.get("phase")],
            "generated_at": gen_at,
        }
        return self._emit(
            decision_type="macro_plan_generated",
            source="ingester.periodization",
            payload=payload,
            evidence_refs=["periodization/macro_plan.json"],
            dry_run=dry_run,
        )

    # ---------- meso_block_created ----------

    def _ingest_meso(self, dry_run: bool) -> int:
        data = self._read_json(self.memory_root / "periodization" / "meso_block.json")
        if data is None:
            return 0
        start, end = data.get("block_start"), data.get("block_end")
        if not start or not end:
            return 0

        prior = self._reader.query(decision_type="meso_block_created")
        seen = {(e.payload.get("block_start"), e.payload.get("block_end")) for e in prior}
        if (start, end) in seen:
            return 0

        payload = {
            "pattern": data.get("pattern"),
            "block_start": start,
            "block_end": end,
            "weeks": len(list(data.get("weekly_load_multipliers") or [])),
            "phase": data.get("phase"),
        }
        return self._emit(
            decision_type="meso_block_created",
            source="ingester.periodization",
            payload=payload,
            evidence_refs=["periodization/meso_block.json"],
            dry_run=dry_run,
        )

    # ---------- micro_cycle_generated ----------

    def _ingest_micro(self, dry_run: bool) -> int:
        dir_ = self.memory_root / "periodization"
        if not dir_.exists():
            return 0

        prior = self._reader.query(decision_type="micro_cycle_generated")
        seen = {e.payload.get("week_start") for e in prior}

        written = 0
        for path in sorted(dir_.glob("micro_cycle_*.json")):
            data = self._read_json(path)
            if data is None:
                continue
            ws = data.get("week_start")
            if not ws or ws in seen:
                continue

            days = list(data.get("days") or [])
            hard_days = sum(
                1 for d in days
                if isinstance(d, dict)
                and str(d.get("tier", "")).upper() not in _SOFT_TIERS
            )
            payload = {
                "week_start": ws,
                "hard_days": hard_days,
                "tss_target": data.get("weekly_tss_target"),
                "phase": data.get("phase"),
            }
            written += self._emit(
                decision_type="micro_cycle_generated",
                source="ingester.periodization",
                payload=payload,
                evidence_refs=[f"periodization/{path.name}"],
                dry_run=dry_run,
            )
            seen.add(ws)
        return written

    # ---------- weekly_plan_assembled ----------

    def _ingest_weekly_plans(self, dry_run: bool) -> int:
        dir_ = self.memory_root / "reports"
        if not dir_.exists():
            return 0

        prior = self._reader.query(decision_type="weekly_plan_assembled")
        seen: set[str] = set()
        for e in prior:
            for ref in e.payload.get("trace_refs") or []:
                seen.add(Path(ref).name)

        written = 0
        for trace_path in sorted(dir_.glob("plan_*.trace.json")):
            if trace_path.name in seen:
                continue
            plan_path = trace_path.with_name(
                trace_path.name.replace(".trace.json", ".json")
            )
            plan_data = self._read_json(plan_path)
            if plan_data is None:
                # trace without paired plan JSON → cannot extract payload; skip.
                _log.event("ledger_ingest_skip_orphan_trace",
                           trace=str(trace_path))
                continue

            days = list(plan_data.get("days") or [])
            session_counter: Counter[str] = Counter()
            for d in days:
                if not isinstance(d, dict):
                    continue
                t = d.get("training_type")
                if not t or t in _NON_SESSION_TYPES:
                    continue
                session_counter[t] += 1

            payload = {
                "plan_date": plan_data.get("week_start"),
                "total_tss": plan_data.get("weekly_tss_target"),
                "sessions_by_type": dict(session_counter),
                "trace_refs": [f"reports/{trace_path.name}"],
            }
            written += self._emit(
                decision_type="weekly_plan_assembled",
                source="ingester.session_designer",
                payload=payload,
                evidence_refs=[
                    f"reports/{trace_path.name}",
                    f"reports/{plan_path.name}",
                ],
                dry_run=dry_run,
            )
            seen.add(trace_path.name)
        return written


# ---------- CLI entry point ----------

def cli_main(argv: list[str] | None = None) -> int:
    """Entry point invoked by `scripts/ingest_ledger.py` (and tests).

    - Resolves memory root (`--memory-root`, default `coach_memory`).
    - Builds an AthleteStateRef snapshot from disk with graceful fallbacks
      (`cp_w_current.json`, `periodization_current.json`,
       `icu_data_warehouse/2_Wellness/wellness_history.json`).
    - Runs the Ingester; prints `{"dry_run": bool, "counts": {...}}` JSON.
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="ingest_ledger",
        description="Backfill ledger entries from Phase 2 artifacts (idempotent).",
    )
    parser.add_argument(
        "--memory-root", type=Path, default=Path("coach_memory"),
        help="Path to coach_memory/ (default: ./coach_memory).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute counts without writing ledger entries.",
    )
    args = parser.parse_args(argv)

    root: Path = args.memory_root
    state = _load_athlete_state_from_disk(root)
    writer = LedgerWriter(root / "ledger" / "decisions.jsonl")
    ingester = Ingester(memory_root=root, writer=writer, athlete_state=state)
    counts = ingester.run(dry_run=args.dry_run)

    print(json.dumps({"dry_run": args.dry_run, "counts": counts}, indent=2))
    return 0


def _load_athlete_state_from_disk(memory_root: Path) -> AthleteStateRef:
    """Best-effort AthleteStateRef assembly for CLI invocation.

    Missing files → use conservative defaults so the ingester can still run.
    This state is used for *this ingestion run* only; real-time consensus /
    adapter writers will capture their own fresh state snapshots.
    """
    from datetime import date as _date

    w_prime = 18000
    phase = "BASE"
    week = 1
    ctl = 0.0
    atl = 0.0

    try:
        cpw = json.loads(
            (memory_root / "physiology" / "cp_w_current.json").read_text(encoding="utf-8")
        )
        w_prime = int(cpw.get("w_prime_joules", w_prime))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass

    try:
        per = json.loads(
            (memory_root / "periodization" / "periodization_current.json").read_text(encoding="utf-8")
        )
        phase = str(per.get("current_phase", phase))
        micro = per.get("micro") or {}
        ws = micro.get("week_start")
        if ws:
            week = _date.fromisoformat(ws).isocalendar().week
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass

    # wellness_history sits beside coach_memory/, not inside it.
    for candidate in (
        memory_root.parent / "icu_data_warehouse" / "2_Wellness" / "wellness_history.json",
        memory_root / "wellness_history.json",
    ):
        try:
            rows = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(rows, list) and rows and isinstance(rows[-1], dict):
                ctl = float(rows[-1].get("ctl") or 0.0)
                atl = float(rows[-1].get("atl") or 0.0)
                break
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            continue

    return AthleteStateRef(
        ctl=ctl, atl=atl, tsb=ctl - atl,
        w_prime=w_prime, phase=phase, week_of_year=max(1, min(53, week)),
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_ingester.py -v`
Expected: PASS all ~22 tests.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/ledger/ingester.py \
        icu/tests/unit/ledger/test_ingester.py
git commit -m "feat(coach-phase3): Ingester — idempotent scan of Phase 2 artifacts"
```

---

## Task 54: `scripts/ingest_ledger.py` CLI — thin wrapper around `cli_main`

**Files:**
- Create: `icu/scripts/ingest_ledger.py`
- Create: `icu/tests/unit/ledger/test_ingest_ledger_cli.py`

**Design notes:**
- The CLI 几乎为零逻辑：`scripts/ingest_ledger.py` 只负责把 `icu/` 根目录加进 `sys.path` 然后调用 `src.coach.ledger.ingester.cli_main`。所有可测逻辑已经在 `ingester.py` 里（T53 已单测）。
- CLI 通过 **subprocess** 调用真实解释器来验收端到端入口 + argparse 接线 + `sys.exit` 语义 —— 这些是 `cli_main` 单测覆盖不到的壳层。
- 不要在 script 内部做任何业务逻辑（见 00-index.md §Execution rules 第 1 条：One file per session / single responsibility）。

- [ ] **Step 1: Write failing tests — subprocess coverage of --help / --dry-run / real run**

Write `icu/tests/unit/ledger/test_ingest_ledger_cli.py`:
```python
"""CLI tests for scripts/ingest_ledger.py — subprocess round-trip of the wrapper."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# icu/tests/unit/ledger/test_ingest_ledger_cli.py → parents[3] = icu/
_ICU_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ICU_ROOT / "scripts" / "ingest_ledger.py"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_ICU_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_script_exists():
    assert _SCRIPT.exists(), f"Expected {_SCRIPT} to exist after T54"


def test_cli_help_exits_zero():
    cp = _run(["--help"], cwd=_ICU_ROOT)
    assert cp.returncode == 0, cp.stderr
    combined = (cp.stdout + cp.stderr).lower()
    assert "--memory-root" in combined
    assert "--dry-run" in combined


def test_cli_dry_run_does_not_write_ledger(tmp_path):
    root = tmp_path / "coach_memory"
    (root / "periodization").mkdir(parents=True)
    (root / "periodization" / "phase_current.json").write_text(
        json.dumps({"phase": "BUILD", "transition_reasons": ["x"]}),
        encoding="utf-8",
    )
    cp = _run(["--memory-root", str(root), "--dry-run"], cwd=tmp_path)
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout)
    assert doc["dry_run"] is True
    assert doc["counts"]["phase_transition"] == 1
    assert not (root / "ledger" / "decisions.jsonl").exists()


def test_cli_real_run_writes_ledger(tmp_path):
    root = tmp_path / "coach_memory"
    (root / "periodization").mkdir(parents=True)
    (root / "periodization" / "phase_current.json").write_text(
        json.dumps({
            "phase": "BUILD",
            "transition_reasons": ["ctl_slope_above_threshold"],
            "ctl_slope_14d": 0.55,
            "override_applied": False,
        }),
        encoding="utf-8",
    )

    cp = _run(["--memory-root", str(root)], cwd=tmp_path)
    assert cp.returncode == 0, cp.stderr

    doc = json.loads(cp.stdout)
    assert doc["dry_run"] is False
    assert doc["counts"]["phase_transition"] == 1

    ledger = root / "ledger" / "decisions.jsonl"
    assert ledger.exists()
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["decision_type"] == "phase_transition"
    assert entry["payload"]["to_phase"] == "BUILD"
    assert entry["payload"]["trigger_rules"] == ["ctl_slope_above_threshold"]


def test_cli_run_twice_is_idempotent(tmp_path):
    root = tmp_path / "coach_memory"
    (root / "periodization").mkdir(parents=True)
    (root / "periodization" / "phase_current.json").write_text(
        json.dumps({"phase": "BUILD", "transition_reasons": ["x"]}),
        encoding="utf-8",
    )
    _run(["--memory-root", str(root)], cwd=tmp_path)
    cp2 = _run(["--memory-root", str(root)], cwd=tmp_path)
    assert cp2.returncode == 0, cp2.stderr
    doc2 = json.loads(cp2.stdout)
    assert doc2["counts"]["phase_transition"] == 0

    lines = (root / "ledger" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_ingest_ledger_cli.py -v`
Expected: FAIL — `test_script_exists` first fails because `scripts/ingest_ledger.py` does not exist.

- [ ] **Step 3: Implement CLI wrapper**

Write `icu/scripts/ingest_ledger.py`:
```python
#!/usr/bin/env python3
"""Backfill the Decision Ledger from Phase 2 artifacts.

Thin wrapper — all logic lives in `src.coach.ledger.ingester.cli_main`.
See docs/superpowers/plans/phase-3/02-ledger-ingester.md for the spec.

Usage:
    python scripts/ingest_ledger.py --memory-root coach_memory [--dry-run]
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure `src.coach.ledger.*` is importable when this script is invoked directly.
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))

from src.coach.ledger.ingester import cli_main  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli_main())
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/ledger/test_ingest_ledger_cli.py -v`
Expected: PASS all 5 tests.

Also re-run the whole ledger suite to guarantee no regressions:
`cd icu && .venv/bin/pytest tests/unit/ledger/ -v`
Expected: PASS all T50–T54 tests (~54 total — 26 from File 01 + 23 from T53 + 5 from T54).

- [ ] **Step 5: Commit**

```bash
git add icu/scripts/ingest_ledger.py \
        icu/tests/unit/ledger/test_ingest_ledger_cli.py
git commit -m "feat(coach-phase3): ingest_ledger.py CLI for one-shot ingestion"
```

---

## End-of-file checkpoint

- [ ] `cd icu && .venv/bin/pytest tests/unit/ledger/ -v` 全绿（~54 tests, T50–T54）
- [ ] 2 次提交完成（T53 / T54 各一次）
- [ ] 运行 `save-progress` 更新 bd 任务 + MEMORY
- [ ] 结束 session。下一个 session 从 [`03-adapter-infrastructure.md`](./03-adapter-infrastructure.md) 开始（T55–T57）。

## Worktree bootstrap reminder (executor reads before Step 1 of T53)

This worktree (`/mnt/d/Cycling-phase3`) should already have File 01 committed and `.venv` / `src/analyzer|utils|fetcher` bootstrapped (see memory `worktree_setup_icu.md`). If this session is a fresh worktree:

```bash
# From /mnt/d/Cycling-phase3 (only if .venv / src/analyzer etc. are missing)
cp -rf /mnt/d/Cycling/icu/.venv icu/.venv
cp -rf /mnt/d/Cycling/icu/src/analyzer icu/src/analyzer
cp -rf /mnt/d/Cycling/icu/src/utils icu/src/utils
cp -rf /mnt/d/Cycling/icu/src/fetcher icu/src/fetcher
```

Sanity check before T53 Step 1:

```bash
cd icu && .venv/bin/pytest tests/unit/ledger/ -v
# Expect T50–T52 tests (from File 01) all green. If not, stop and repair the
# worktree before touching T53.
```
