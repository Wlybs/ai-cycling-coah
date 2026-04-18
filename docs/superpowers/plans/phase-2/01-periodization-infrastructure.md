# Phase 2 — Periodization infrastructure (Tasks T25–T27)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Files covered:**
- `icu/src/coach/periodization/__init__.py`
- `icu/src/coach/periodization/types.py`
- `icu/src/coach/periodization/snapshot_io.py`
- `icu/tests/unit/periodization/test_types.py`
- `icu/tests/unit/periodization/test_snapshot_io.py`

---

## Task 25: Package scaffold & enums

**Files:**
- Create: `icu/src/coach/periodization/__init__.py`
- Create: `icu/src/coach/periodization/types.py` (enums only — models come in T26)
- Create: `icu/tests/unit/periodization/__init__.py`
- Create: `icu/tests/unit/periodization/test_types.py`

- [ ] **Step 1: Write failing test — enums exist with correct values**

Write `icu/tests/unit/periodization/test_types.py`:
```python
from src.coach.periodization.types import Phase, IntensityTier, SessionType

def test_phase_enum_values():
    expected = {"BASE", "BUILD", "PEAK", "TAPER", "RACE", "TRANSITION"}
    assert {p.value for p in Phase} == expected

def test_intensity_tier_ordering():
    tiers = [IntensityTier.REST, IntensityTier.EASY, IntensityTier.MEDIUM,
             IntensityTier.HARD, IntensityTier.RACE_SIM]
    # 约定：order 由 ordinal 属性保证
    ordinals = [t.ordinal for t in tiers]
    assert ordinals == sorted(ordinals)

def test_session_type_matches_legacy_training_type():
    # 必须与 plan_generator.DayPlan.training_type Literal 一致，ICU 日历同步依赖
    expected = {"Rest", "Recovery", "Aerobic", "Tempo",
                "Threshold", "VO2max", "Neuromuscular", "Race"}
    assert {s.value for s in SessionType} == expected
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement enums**

Write `icu/src/coach/periodization/__init__.py`:
```python
"""Periodization Engine — 宏观/中观/微观三层周期化。

入口：
  refresh_periodization(warehouse_dir, memory_dir, wellness_list, events_list,
                        physiology_snapshot_dir) -> PeriodizationSnapshot
见 05-micro-cycle.md T35 的 engine facade 实现。
"""
```

Write `icu/src/coach/periodization/types.py`:
```python
"""Periodization 层的类型定义。所有对外暴露的数据结构都是 Pydantic 模型。"""
from __future__ import annotations

from enum import Enum


class Phase(str, Enum):
    """周期化阶段。取值与 Scheme 4 蓝图一致。"""
    BASE = "BASE"
    BUILD = "BUILD"
    PEAK = "PEAK"
    TAPER = "TAPER"
    RACE = "RACE"
    TRANSITION = "TRANSITION"


class IntensityTier(str, Enum):
    """当日强度等级。用于 MicroCycle 的 7 日序列。"""
    REST = "REST"
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    RACE_SIM = "RACE_SIM"

    @property
    def ordinal(self) -> int:
        """相对顺序值，仅用于排序比较，不代表训练负荷（TSS/W 等）。"""
        return {
            "REST": 0,
            "EASY": 1,
            "MEDIUM": 2,
            "HARD": 3,
            "RACE_SIM": 4,
        }[self.value]


class SessionType(str, Enum):
    """与旧 plan_generator.DayPlan.training_type Literal 严格一致。

    任何值改动都会破坏 ICU 日历同步兼容性 — 务必保持。"""
    REST = "Rest"
    RECOVERY = "Recovery"
    AEROBIC = "Aerobic"
    TEMPO = "Tempo"
    THRESHOLD = "Threshold"
    VO2MAX = "VO2max"
    NEUROMUSCULAR = "Neuromuscular"
    RACE = "Race"
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_types.py -v`
Expected: PASS all three.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/__init__.py \
        icu/src/coach/periodization/types.py \
        icu/tests/unit/periodization/__init__.py \
        icu/tests/unit/periodization/test_types.py
git commit -m "feat(coach-phase2): periodization package scaffold with Phase/IntensityTier/SessionType enums"
```

---

## Task 26: Pydantic models — PhaseIntent, MacroPlan, MesoBlock, MicroCycle, PeriodizationSnapshot

**Files:**
- Modify: `icu/src/coach/periodization/types.py` (append models)
- Modify: `icu/tests/unit/periodization/test_types.py` (append tests)

- [ ] **Step 1: Write failing tests — model roundtrip + required fields**

Append to `icu/tests/unit/periodization/test_types.py`:
```python
from datetime import date
import pytest
from pydantic import ValidationError

from src.coach.periodization.types import (
    PhaseIntent, MacroPlan, MacroWindow, MesoBlock, MicroCycle, DayIntent,
    PeriodizationSnapshot, Phase, IntensityTier,
)


def test_phase_intent_required_fields():
    intent = PhaseIntent(
        phase=Phase.BUILD,
        primary_adaptation="threshold_capacity",
        weekly_tss_target=550,
        intensity_distribution_pct={"low": 70, "mid": 20, "high": 10},
        rest_days_per_week=1,
        rationale="Base done; CTL 94 stable; build 4-week block.",
    )
    assert intent.phase is Phase.BUILD
    assert sum(intent.intensity_distribution_pct.values()) == 100


def test_phase_intent_invalid_distribution_rejected():
    with pytest.raises(ValidationError):
        PhaseIntent(
            phase=Phase.BASE,
            primary_adaptation="aerobic_base",
            weekly_tss_target=450,
            intensity_distribution_pct={"low": 60, "mid": 20, "high": 10},  # sum=90
            rest_days_per_week=1,
            rationale="x",
        )


def test_macro_window_has_dates_and_intent():
    w = MacroWindow(
        phase=Phase.TAPER,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 10),
        intent=PhaseIntent(
            phase=Phase.TAPER,
            primary_adaptation="freshness_preservation",
            weekly_tss_target=300,
            intensity_distribution_pct={"low": 60, "mid": 10, "high": 30},
            rest_days_per_week=2,
            rationale="Mujika 2009 taper: vol -50%, intensity preserved.",
        ),
    )
    assert (w.end_date - w.start_date).days == 9


def test_micro_cycle_seven_day_intents_required():
    days = [
        DayIntent(day_of_week="Mon", tier=IntensityTier.REST,
                  target_tss=0, session_hint="complete rest"),
        DayIntent(day_of_week="Tue", tier=IntensityTier.HARD,
                  target_tss=95, session_hint="VO2max"),
        DayIntent(day_of_week="Wed", tier=IntensityTier.EASY,
                  target_tss=40, session_hint="recovery spin"),
        DayIntent(day_of_week="Thu", tier=IntensityTier.MEDIUM,
                  target_tss=75, session_hint="tempo"),
        DayIntent(day_of_week="Fri", tier=IntensityTier.REST,
                  target_tss=0, session_hint="rest"),
        DayIntent(day_of_week="Sat", tier=IntensityTier.HARD,
                  target_tss=110, session_hint="threshold"),
        DayIntent(day_of_week="Sun", tier=IntensityTier.EASY,
                  target_tss=130, session_hint="long Z2"),
    ]
    cycle = MicroCycle(
        week_start=date(2026, 4, 20),
        week_end=date(2026, 4, 26),
        phase=Phase.BUILD,
        intent=days[1],  # primary intent of the week — here, threshold/VO2max
        days=days,
        weekly_tss_target=450,
    )
    assert len(cycle.days) == 7
    assert cycle.weekly_tss_target == 450


def test_micro_cycle_rejects_non_seven_day():
    with pytest.raises(ValidationError):
        MicroCycle(
            week_start=date(2026, 4, 20),
            week_end=date(2026, 4, 26),
            phase=Phase.BUILD,
            intent=DayIntent(day_of_week="Mon", tier=IntensityTier.REST,
                             target_tss=0, session_hint="rest"),
            days=[],  # empty
            weekly_tss_target=450,
        )


def test_periodization_snapshot_composition():
    intent = PhaseIntent(
        phase=Phase.BUILD, primary_adaptation="threshold",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="x",
    )
    macro = MacroPlan(
        generated_at="2026-04-18T00:00:00Z",
        season_end_date=date(2026, 9, 30),
        windows=[MacroWindow(
            phase=Phase.BUILD, start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 28), intent=intent,
        )],
    )
    meso = MesoBlock(
        pattern="3:1",
        block_start=date(2026, 4, 6), block_end=date(2026, 4, 26),
        weekly_load_multipliers=[1.0, 1.05, 1.1, 0.7],
        phase=Phase.BUILD,
    )
    micro = MicroCycle(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        phase=Phase.BUILD, intent=intent,
        days=[DayIntent(day_of_week=d, tier=IntensityTier.EASY,
                        target_tss=40, session_hint="x")
              for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]],
        weekly_tss_target=450,
    )
    snap = PeriodizationSnapshot(
        generated_at="2026-04-18T00:00:00Z",
        current_phase=Phase.BUILD,
        macro=macro, meso=meso, micro=micro,
        next_race=None,
    )
    js = snap.model_dump_json()
    assert "BUILD" in js
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_types.py -v`
Expected: FAIL — classes undefined.

- [ ] **Step 3: Implement models**

Append to `icu/src/coach/periodization/types.py`:
```python
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class PhaseIntent(BaseModel):
    """单个阶段的生理学意图。周期化引擎的对外主数据结构。"""
    phase: Phase
    primary_adaptation: str = Field(
        ...,
        description="本阶段主要想追的适应，如 'aerobic_base' / 'threshold_capacity' "
                    "/ 'vo2_power' / 'freshness_preservation'。",
    )
    weekly_tss_target: int = Field(..., ge=0, le=1200)
    intensity_distribution_pct: dict[str, int] = Field(
        ...,
        description="低/中/高强度占比，必须 sum=100。key 固定为 'low' | 'mid' | 'high'。",
    )
    rest_days_per_week: int = Field(..., ge=0, le=7)
    rationale: str = Field(..., description="给 LLM 看的决策理由，可含文献引用。")

    @model_validator(mode="after")
    def _check_distribution_sum(self):
        if set(self.intensity_distribution_pct.keys()) != {"low", "mid", "high"}:
            raise ValueError("intensity_distribution_pct keys must be {'low','mid','high'}")
        if sum(self.intensity_distribution_pct.values()) != 100:
            raise ValueError("intensity_distribution_pct must sum to 100")
        return self


class MacroWindow(BaseModel):
    """宏观阶段窗口（一段 Base / Build / Peak / Taper / Race / Transition 连续区间）。"""
    phase: Phase
    start_date: date
    end_date: date
    intent: PhaseIntent

    @model_validator(mode="after")
    def _check_order(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class MacroPlan(BaseModel):
    """整个赛季的阶段布局。"""
    generated_at: str
    season_end_date: date
    windows: list[MacroWindow] = Field(..., min_length=1)


class MesoBlock(BaseModel):
    """中观训练块 (通常 3–6 周)。"""
    pattern: str = Field(..., description="'3:1' | '2:1' | 'polarized' | 'linear'")
    block_start: date
    block_end: date
    weekly_load_multipliers: list[float] = Field(..., min_length=3, max_length=6)
    phase: Phase


class DayIntent(BaseModel):
    """当周单日意图。"""
    day_of_week: str = Field(..., pattern="^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$")
    tier: IntensityTier
    target_tss: int = Field(..., ge=0, le=400)
    session_hint: str = Field(
        ..., description="给 Session Designer 的提示：期望哪种 session_type 或结构。"
    )


class MicroCycle(BaseModel):
    """当前一周的 7 日意图序列。"""
    week_start: date
    week_end: date
    phase: Phase
    intent: PhaseIntent
    days: list[DayIntent] = Field(..., min_length=7, max_length=7)
    weekly_tss_target: int = Field(..., ge=0, le=1200)


class NextRace(BaseModel):
    name: str
    race_date: date
    priority: str = Field(..., pattern="^(A|B|C)$")
    course_hint: Optional[str] = None


class PeriodizationSnapshot(BaseModel):
    """汇总快照。写入 coach_memory/periodization/periodization_current.json。"""
    generated_at: str
    current_phase: Phase
    macro: MacroPlan
    meso: MesoBlock
    micro: MicroCycle
    next_race: Optional[NextRace] = None
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_types.py -v`
Expected: PASS all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/types.py icu/tests/unit/periodization/test_types.py
git commit -m "feat(coach-phase2): add periodization Pydantic models (PhaseIntent/Macro/Meso/Micro/Snapshot)"
```

---

## Task 27: Snapshot IO — read/write periodization JSON files

**Files:**
- Create: `icu/src/coach/periodization/snapshot_io.py`
- Create: `icu/tests/unit/periodization/test_snapshot_io.py`

- [ ] **Step 1: Write failing test — write_snapshot + load_snapshot roundtrip**

Write `icu/tests/unit/periodization/test_snapshot_io.py`:
```python
import json
from datetime import date
from pathlib import Path

from src.coach.periodization.snapshot_io import (
    write_phase_current, write_macro_plan, write_meso_block,
    write_micro_cycle, write_periodization_snapshot,
    load_periodization_snapshot,
)
from src.coach.periodization.types import (
    Phase, PhaseIntent, MacroPlan, MacroWindow, MesoBlock, MicroCycle,
    DayIntent, IntensityTier, PeriodizationSnapshot,
)


def _make_intent(phase=Phase.BUILD):
    return PhaseIntent(
        phase=phase, primary_adaptation="threshold_capacity",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )


def _make_micro(phase=Phase.BUILD, week_start=date(2026, 4, 20)):
    return MicroCycle(
        week_start=week_start, week_end=date(2026, 4, 26),
        phase=phase, intent=_make_intent(phase),
        days=[DayIntent(day_of_week=d, tier=IntensityTier.EASY,
                        target_tss=40, session_hint="x")
              for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]],
        weekly_tss_target=450,
    )


def test_write_phase_current_creates_file(tmp_path):
    base = tmp_path / "coach_memory" / "periodization"
    path = write_phase_current(
        base_dir=base, phase=Phase.BUILD,
        reasons=["CTL slope +0.3/d over 4w", "no race within 4w"],
        now_iso="2026-04-18T00:00:00Z",
    )
    assert Path(path).exists()
    doc = json.loads(Path(path).read_text())
    assert doc["current_phase"] == "BUILD"
    assert "CTL slope" in doc["reasons"][0]


def test_write_and_load_snapshot_roundtrip(tmp_path):
    base = tmp_path / "coach_memory" / "periodization"
    intent = _make_intent()
    macro = MacroPlan(
        generated_at="2026-04-18T00:00:00Z",
        season_end_date=date(2026, 9, 30),
        windows=[MacroWindow(phase=Phase.BUILD, start_date=date(2026, 4, 1),
                             end_date=date(2026, 4, 28), intent=intent)],
    )
    meso = MesoBlock(
        pattern="3:1",
        block_start=date(2026, 4, 6), block_end=date(2026, 4, 26),
        weekly_load_multipliers=[1.0, 1.05, 1.1, 0.7], phase=Phase.BUILD,
    )
    micro = _make_micro()
    snap = PeriodizationSnapshot(
        generated_at="2026-04-18T00:00:00Z",
        current_phase=Phase.BUILD, macro=macro, meso=meso, micro=micro,
    )
    path = write_periodization_snapshot(base, snap)
    loaded = load_periodization_snapshot(base)
    assert loaded is not None
    assert loaded.current_phase is Phase.BUILD
    assert loaded.micro.weekly_tss_target == 450
    # 同时写了 micro_cycle_YYYY-WW.json
    assert any((base.glob("micro_cycle_*.json")))


def test_load_missing_returns_none(tmp_path):
    assert load_periodization_snapshot(tmp_path / "nope") is None
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_snapshot_io.py -v`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement IO module**

Write `icu/src/coach/periodization/snapshot_io.py`:
```python
"""Periodization snapshot JSON 读写。所有路径都相对 base_dir。"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from .types import (
    MacroPlan, MesoBlock, MicroCycle, PeriodizationSnapshot, Phase,
)

PHASE_CURRENT = "phase_current.json"
MACRO_PLAN = "macro_plan.json"
MESO_BLOCK = "meso_block.json"
SNAPSHOT = "periodization_current.json"


def _ensure_dir(base_dir: Path) -> Path:
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def write_phase_current(
    base_dir: Path, phase: Phase, reasons: list[str], now_iso: str
) -> str:
    base = _ensure_dir(base_dir)
    doc = {
        "generated_at": now_iso,
        "current_phase": phase.value,
        "reasons": reasons,
    }
    path = base / PHASE_CURRENT
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    return str(path)


def write_macro_plan(base_dir: Path, macro: MacroPlan) -> str:
    base = _ensure_dir(base_dir)
    path = base / MACRO_PLAN
    path.write_text(macro.model_dump_json(indent=2))
    return str(path)


def write_meso_block(base_dir: Path, meso: MesoBlock) -> str:
    base = _ensure_dir(base_dir)
    path = base / MESO_BLOCK
    path.write_text(meso.model_dump_json(indent=2))
    return str(path)


def _micro_filename(micro: MicroCycle) -> str:
    iso_year, iso_week, _ = micro.week_start.isocalendar()
    return f"micro_cycle_{iso_year}-W{iso_week:02d}.json"


def write_micro_cycle(base_dir: Path, micro: MicroCycle) -> str:
    base = _ensure_dir(base_dir)
    path = base / _micro_filename(micro)
    path.write_text(micro.model_dump_json(indent=2))
    return str(path)


def write_periodization_snapshot(
    base_dir: Path, snap: PeriodizationSnapshot
) -> str:
    """写入总快照 + 同步写入 phase_current / macro / meso / micro。"""
    base = _ensure_dir(base_dir)
    write_phase_current(
        base, snap.current_phase,
        reasons=[f"Snapshot regenerated at {snap.generated_at}"],
        now_iso=snap.generated_at,
    )
    write_macro_plan(base, snap.macro)
    write_meso_block(base, snap.meso)
    write_micro_cycle(base, snap.micro)
    path = base / SNAPSHOT
    path.write_text(snap.model_dump_json(indent=2))
    return str(path)


def load_periodization_snapshot(base_dir: Path) -> Optional[PeriodizationSnapshot]:
    path = Path(base_dir) / SNAPSHOT
    if not path.exists():
        return None
    try:
        return PeriodizationSnapshot.model_validate_json(path.read_text())
    except Exception:
        return None
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/ -v`
Expected: PASS all tests across both test files.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/snapshot_io.py \
        icu/tests/unit/periodization/test_snapshot_io.py
git commit -m "feat(coach-phase2): periodization snapshot IO (write/load + split files per layer)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/periodization/ -v` 全绿
- [ ] 3 次提交完成（T25 / T26 / T27 各一次）
- [ ] 运行 `save-progress` 更新 bd 任务 + MEMORY
- [ ] 结束 session。下一个 session 从 [`02-phase-detector.md`](./02-phase-detector.md) 开始。
