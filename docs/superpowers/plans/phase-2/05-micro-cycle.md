# Phase 2 — Micro cycle + engine facade (Tasks T34–T35)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/periodization/micro_cycle.py`
- `icu/src/coach/periodization/engine.py`
- `icu/tests/unit/periodization/test_micro_cycle.py`
- `icu/tests/unit/periodization/test_engine.py`

**Goal:** 把 `PhaseIntent + MesoBlock + 当前周索引` 塑形为具体的 7 日 `DayIntent` 序列；然后用一个 facade 把 phase_detector → macro → meso → micro 串起来，产出并持久化 `PeriodizationSnapshot`。

---

## Task 34: Micro cycle builder

**Goal:** 给定当前 `PhaseIntent`、当前 Meso 块的周索引（0,1,2,...），返回一个 `MicroCycle`：
- `weekly_tss_target = intent.weekly_tss_target * meso.weekly_load_multipliers[week_idx]`
- 7 日 `DayIntent` 序列按 Phase+Meso 的默认模板分配 tier 和 session_hint（见下表）
- 具体比例按 intent.intensity_distribution_pct 调整 target_tss per day

### 每周 tier 分配模板（ground truth）

| Phase | Mon | Tue | Wed | Thu | Fri | Sat | Sun | 说明 |
|---|---|---|---|---|---|---|---|---|
| BASE | REST | MEDIUM (tempo) | EASY | EASY | REST | MEDIUM (endurance) | EASY (long Z2) | 极化，重长骑 |
| BUILD | REST | HARD (threshold or VO2) | EASY | MEDIUM (sweet-spot) | REST | HARD (long intervals) | MEDIUM (long endurance) | 2 hard days，间隔 ≥48h |
| PEAK | REST | HARD (short VO2) | EASY | MEDIUM (tempo) | REST | HARD (race-sim) | EASY (endurance) | 保量减 volume，尖锐刺激 |
| TAPER | REST | HARD (short openers) | EASY | MEDIUM (short tempo) | REST | EASY (short Z2) | REST | 量砍一半，强度保 |
| RACE | REST | EASY (openers) | REST | EASY (short) | REST | RACE_SIM (race day) | REST | 赛前 / 赛日 / 赛后 |
| TRANSITION | REST | EASY | REST | EASY | REST | EASY | EASY | 全 Z1/Z2 无结构 |

若 intent.rest_days_per_week ≥ 2，把 session_hint == REST 的其中一个向后推到 Fri；如果已经 2 个 REST 就原样保留。

**Files:**
- Create: `icu/src/coach/periodization/micro_cycle.py`
- Create: `icu/tests/unit/periodization/test_micro_cycle.py`

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/periodization/test_micro_cycle.py`:
```python
from datetime import date

from src.coach.periodization.micro_cycle import build_micro_cycle
from src.coach.periodization.types import (
    Phase, PhaseIntent, MesoBlock, IntensityTier,
)


def _intent(phase: Phase, tss: int = 500, rest: int = 1) -> PhaseIntent:
    return PhaseIntent(
        phase=phase, primary_adaptation="x",
        weekly_tss_target=tss,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=rest, rationale="test",
    )


def _meso(phase: Phase = Phase.BUILD) -> MesoBlock:
    return MesoBlock(
        pattern="3:1",
        block_start=date(2026, 4, 13), block_end=date(2026, 5, 10),
        weekly_load_multipliers=[1.00, 1.05, 1.10, 0.70],
        phase=phase,
    )


def test_build_week_applies_load_multiplier_to_tss_target():
    intent = _intent(Phase.BUILD, tss=500)
    meso = _meso()
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20),  # week 2 of 4-week block (idx=1)
        meso=meso,
        intent=intent,
        week_idx=1,
    )
    # multiplier 1.05 → target 525
    assert wk.weekly_tss_target == 525
    assert wk.phase is Phase.BUILD


def test_build_week_has_7_days_and_rest_placement():
    intent = _intent(Phase.BUILD, rest=1)
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20),
        meso=_meso(), intent=intent, week_idx=0,
    )
    dow = [d.day_of_week for d in wk.days]
    assert dow == ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    # Build 模板：Mon + Fri 默认 REST（其实 template 指定 Mon=REST Fri=REST）
    rest_days = [d for d in wk.days if d.tier is IntensityTier.REST]
    assert len(rest_days) >= 1


def test_build_week_two_rest_days_when_intent_requires():
    intent = _intent(Phase.TAPER, rest=2)
    meso = _meso(phase=Phase.TAPER).model_copy(
        update={"weekly_load_multipliers": [1.0, 0.7, 0.4]})
    wk = build_micro_cycle(
        week_start=date(2026, 5, 4), meso=meso, intent=intent, week_idx=0,
    )
    rests = [d for d in wk.days if d.tier is IntensityTier.REST]
    assert len(rests) >= 2


def test_build_week_high_intensity_days_spaced():
    intent = _intent(Phase.BUILD)
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20), meso=_meso(), intent=intent, week_idx=0,
    )
    hard_indices = [i for i, d in enumerate(wk.days)
                    if d.tier is IntensityTier.HARD]
    # 相邻 HARD day 之间至少有一个非 HARD 日
    for i in range(len(hard_indices) - 1):
        assert hard_indices[i+1] - hard_indices[i] >= 2


def test_build_week_tss_sum_within_15pct_of_target():
    intent = _intent(Phase.BUILD, tss=500)
    wk = build_micro_cycle(
        week_start=date(2026, 4, 20), meso=_meso(), intent=intent, week_idx=0,
    )
    actual = sum(d.target_tss for d in wk.days)
    diff = abs(actual - wk.weekly_tss_target)
    assert diff <= wk.weekly_tss_target * 0.15


def test_base_phase_uses_z2_dominant_hints():
    intent = _intent(Phase.BASE)
    wk = build_micro_cycle(
        week_start=date(2026, 2, 2), meso=_meso(phase=Phase.BASE),
        intent=intent, week_idx=0,
    )
    # No HARD days in BASE
    assert all(d.tier is not IntensityTier.HARD for d in wk.days)
    hints = " ".join(d.session_hint for d in wk.days).lower()
    assert "z2" in hints or "endurance" in hints or "long" in hints


def test_week_primary_intent_matches_phase():
    intent = _intent(Phase.PEAK)
    meso = _meso(phase=Phase.PEAK)
    wk = build_micro_cycle(
        week_start=date(2026, 5, 4), meso=meso, intent=intent, week_idx=0,
    )
    assert wk.intent.phase is Phase.PEAK
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement micro_cycle**

Write `icu/src/coach/periodization/micro_cycle.py`:
```python
"""Micro cycle builder：把 PhaseIntent × MesoBlock × week_idx 落地成 7 日 DayIntent 序列。"""
from __future__ import annotations

from datetime import date, timedelta

from .types import (
    DayIntent, IntensityTier, MesoBlock, MicroCycle, Phase, PhaseIntent,
)

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 每 Phase 的 7 日 tier+hint 模板
_TEMPLATES: dict[Phase, list[tuple[IntensityTier, str]]] = {
    Phase.BASE: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.MEDIUM, "tempo endurance 60-75min"),
        (IntensityTier.EASY,   "Z2 recovery spin"),
        (IntensityTier.EASY,   "Z2 endurance 75-90min"),
        (IntensityTier.REST,   "rest or short Z1"),
        (IntensityTier.MEDIUM, "endurance 90min with short sweet-spot burst"),
        (IntensityTier.EASY,   "long Z2 3h+"),
    ],
    Phase.BUILD: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "VO2max 5x4' @ 110-115% CP"),
        (IntensityTier.EASY,   "Z2 recovery 45min"),
        (IntensityTier.MEDIUM, "sweet-spot 3x12' @ 88-93% CP"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "threshold 2x20' @ 97-102% CP"),
        (IntensityTier.MEDIUM, "endurance 2.5-3h with 2x10' tempo"),
    ],
    Phase.PEAK: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "VO2max short 6x3' @ 115-120% CP"),
        (IntensityTier.EASY,   "Z2 recovery 45min"),
        (IntensityTier.MEDIUM, "tempo 60-75min"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "race-sim intervals (course-specific)"),
        (IntensityTier.EASY,   "endurance 90-120min"),
    ],
    Phase.TAPER: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.HARD,   "short openers 3x3' @ 110% CP"),
        (IntensityTier.EASY,   "Z2 30-45min"),
        (IntensityTier.MEDIUM, "short tempo 30min"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.EASY,   "short Z2 45min + 3x30'' openers"),
        (IntensityTier.REST,   "rest (day before race area)"),
    ],
    Phase.RACE: [
        (IntensityTier.REST,   "rest"),
        (IntensityTier.EASY,   "30min Z2 + 4x30'' openers"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.EASY,   "20min activation + 3x30'' openers"),
        (IntensityTier.REST,   "rest"),
        (IntensityTier.RACE_SIM,"RACE"),
        (IntensityTier.REST,   "rest + recovery"),
    ],
    Phase.TRANSITION: [
        (IntensityTier.REST,  "rest"),
        (IntensityTier.EASY,  "Z1/Z2 outdoor unstructured"),
        (IntensityTier.REST,  "rest"),
        (IntensityTier.EASY,  "Z2 easy 60min"),
        (IntensityTier.REST,  "rest"),
        (IntensityTier.EASY,  "Z2 outdoor 90min"),
        (IntensityTier.EASY,  "Z2 easy 60min"),
    ],
}

# 每 tier 的相对 TSS 权重（按 1 周 7 日汇总归一到 weekly_tss_target）
_TIER_TSS_WEIGHT = {
    IntensityTier.REST: 0.0,
    IntensityTier.EASY: 0.5,
    IntensityTier.MEDIUM: 1.0,
    IntensityTier.HARD: 1.4,
    IntensityTier.RACE_SIM: 2.0,
}


def _apply_extra_rest(days: list[tuple[IntensityTier, str]],
                      rest_days_required: int) -> list[tuple[IntensityTier, str]]:
    """如果 intent 要 ≥2 rest 但模板只有 1 个，把 Fri 改成 REST。"""
    current_rests = sum(1 for t, _ in days if t is IntensityTier.REST)
    if current_rests >= rest_days_required:
        return days
    out = list(days)
    # 4 号位（周五）若非 REST，改成 REST
    if out[4][0] is not IntensityTier.REST:
        out[4] = (IntensityTier.REST, "rest (additional per intent)")
    return out


def _distribute_tss(week_tss: int,
                    tiers: list[IntensityTier]) -> list[int]:
    weights = [_TIER_TSS_WEIGHT[t] for t in tiers]
    total_w = sum(weights) or 1.0
    raw = [week_tss * w / total_w for w in weights]
    ints = [int(round(v)) for v in raw]
    # 校正四舍五入误差，让总和等于 week_tss
    delta = week_tss - sum(ints)
    if ints:
        # 把 delta 加在第一个非零项上
        for i in range(len(ints)):
            if weights[i] > 0:
                ints[i] += delta
                break
    return ints


def build_micro_cycle(
    week_start: date,
    meso: MesoBlock,
    intent: PhaseIntent,
    week_idx: int,
) -> MicroCycle:
    """核心构造函数。week_idx 从 0 开始，指向 meso.weekly_load_multipliers 中的对应项。"""
    template = _TEMPLATES[meso.phase]
    template = _apply_extra_rest(template, intent.rest_days_per_week)

    multiplier = meso.weekly_load_multipliers[
        min(week_idx, len(meso.weekly_load_multipliers) - 1)
    ]
    week_tss = int(round(intent.weekly_tss_target * multiplier))

    tiers = [t for t, _ in template]
    tss_per_day = _distribute_tss(week_tss, tiers)

    days: list[DayIntent] = []
    for i, (tier, hint) in enumerate(template):
        days.append(DayIntent(
            day_of_week=DOW[i], tier=tier,
            target_tss=max(0, tss_per_day[i]),
            session_hint=hint,
        ))

    return MicroCycle(
        week_start=week_start,
        week_end=week_start + timedelta(days=6),
        phase=meso.phase,
        intent=intent,
        days=days,
        weekly_tss_target=week_tss,
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_micro_cycle.py -v`
Expected: PASS all seven.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/micro_cycle.py \
        icu/tests/unit/periodization/test_micro_cycle.py
git commit -m "feat(coach-phase2): micro cycle builder (per-phase 7-day template + TSS distribution)"
```

---

## Task 35: Engine facade — assemble full PeriodizationSnapshot

**Goal:** 一个 `refresh_periodization()` 函数：
1. 读 `icu_data_warehouse/2_Wellness/wellness_history.json` → `analyze_ctl_slope()`
2. 读 `icu_data_warehouse/8_Events/events.json` + `coach_memory/race_calendar.md` → `load_race_calendar()` → `next_race_after()`
3. 读 `coach_memory/deep_analysis/summary_latest.json` → 取最近 3 次 `stimulus_score` 中位数（Phase 1 的 summary 存了当次；此处需要一个"过去 N 次"聚合，直接遍历 `coach_memory/deep_analysis/*.trace.json` 读 `stimulus_score` 字段——若不存在该字段，降级为 None）
4. 调 `detect_phase()` → `Phase`
5. 调 `plan_macro()` → `MacroPlan`
6. 定位当前所在 `MacroWindow`
7. 调 `select_meso_pattern()` + `build_meso_block()` → `MesoBlock`
8. 计算当前周索引 = (reference_date_monday − meso.block_start).days // 7
9. 调 `build_intent_for_phase()` → `PhaseIntent`
10. 调 `build_micro_cycle()` → `MicroCycle`
11. 组合 `PeriodizationSnapshot` → `write_periodization_snapshot()`
12. 结构化日志（`src.coach.common.logging.get_logger("periodization_engine")`）每步的 duration、status

**Files:**
- Create: `icu/src/coach/periodization/engine.py`
- Create: `icu/tests/unit/periodization/test_engine.py`

- [ ] **Step 1: Write failing test — integration with mocked warehouse**

Write `icu/tests/unit/periodization/test_engine.py`:
```python
import json
from datetime import date
from pathlib import Path

from src.coach.periodization.engine import refresh_periodization
from src.coach.periodization.snapshot_io import load_periodization_snapshot
from src.coach.periodization.types import Phase


def _seed_warehouse(tmp_path):
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "2_Wellness").mkdir(parents=True)
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "1_Profile").mkdir(parents=True)
    # Wellness with rising CTL over 30 days
    wellness = [
        {"id": f"2026-03-{d:02d}", "ctl": 80 + (d - 1) * 0.4, "atl": 90}
        for d in range(1, 32)
    ] + [
        {"id": f"2026-04-{d:02d}", "ctl": 92 + d * 0.2, "atl": 95}
        for d in range(1, 19)
    ]
    (warehouse / "2_Wellness" / "wellness_history.json").write_text(
        json.dumps(wellness))
    # A race in 58 days
    events = [{"id": 1, "category": "RACE", "name": "Goal",
               "start_date_local": "2026-06-15T08:00:00"}]
    (warehouse / "8_Events" / "events.json").write_text(json.dumps(events))
    (warehouse / "1_Profile" / "athlete.json").write_text(
        json.dumps({"ftp": 288, "hr_max": 195, "weight": 62}))
    return warehouse


def _seed_memory(tmp_path):
    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    # summary_latest with stimulus_score 0.55
    (mem / "deep_analysis" / "summary_latest.json").write_text(json.dumps({
        "stimulus_score": 0.55, "progression_flag": "progression",
        "headline_verdict": "solid threshold work",
    }))
    return mem


def test_refresh_periodization_writes_snapshot(tmp_path):
    warehouse = _seed_warehouse(tmp_path)
    memory = _seed_memory(tmp_path)
    result = refresh_periodization(
        warehouse_dir=warehouse,
        memory_dir=memory,
        reference_date=date(2026, 4, 18),
        generated_at="2026-04-18T00:00:00Z",
    )
    assert result["status"] == "ok"
    snap = load_periodization_snapshot(memory / "periodization")
    assert snap is not None
    # 距离 race 58 天 + CTL 增加 → 应该被判为 BUILD
    assert snap.current_phase is Phase.BUILD
    assert snap.micro.weekly_tss_target > 0
    assert len(snap.micro.days) == 7


def test_refresh_handles_missing_wellness_gracefully(tmp_path):
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "8_Events" / "events.json").write_text("[]")
    memory = tmp_path / "coach_memory"
    memory.mkdir()
    result = refresh_periodization(
        warehouse_dir=warehouse, memory_dir=memory,
        reference_date=date(2026, 4, 18),
        generated_at="2026-04-18T00:00:00Z",
    )
    # 无 wellness → slope unknown → 走 fallback BUILD
    assert result["status"] == "ok"
    snap = load_periodization_snapshot(memory / "periodization")
    assert snap is not None
    assert snap.current_phase in (Phase.BUILD, Phase.BASE, Phase.TRANSITION)


def test_refresh_captures_next_race_when_present(tmp_path):
    warehouse = _seed_warehouse(tmp_path)
    memory = _seed_memory(tmp_path)
    refresh_periodization(
        warehouse_dir=warehouse, memory_dir=memory,
        reference_date=date(2026, 4, 18),
        generated_at="2026-04-18T00:00:00Z",
    )
    snap = load_periodization_snapshot(memory / "periodization")
    assert snap.next_race is not None
    assert snap.next_race.name == "Goal"
    assert snap.next_race.days_out == (date(2026, 6, 15) - date(2026, 4, 18)).days
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement engine**

Write `icu/src/coach/periodization/engine.py`:
```python
"""Periodization engine facade — 把 phase detection / macro / meso / micro 串起来。"""
from __future__ import annotations

import json
import time
import statistics
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from ..common.logging import get_logger
from .ctl_slope import analyze_ctl_slope
from .intent_library import build_intent_for_phase
from .macro_planner import plan_macro
from .meso_builder import build_meso_block, select_meso_pattern
from .micro_cycle import build_micro_cycle
from .phase_detector import detect_phase
from .race_calendar import load_race_calendar, next_race_after
from .snapshot_io import write_periodization_snapshot
from .types import (
    MacroPlan, MacroWindow, MesoBlock, MicroCycle, NextRace,
    Phase, PeriodizationSnapshot, PhaseIntent,
)

LOG = get_logger("periodization_engine")


def _load_wellness(warehouse_dir: Path) -> list[dict]:
    path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_athlete(warehouse_dir: Path) -> dict:
    path = warehouse_dir / "1_Profile" / "athlete.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_stimulus_median(memory_dir: Path) -> Optional[float]:
    """Median stimulus_score from coach_memory/deep_analysis/*.trace.json (fallback to summary_latest)."""
    deep_dir = memory_dir / "deep_analysis"
    if not deep_dir.exists():
        return None
    scores: list[float] = []
    for tp in sorted(deep_dir.glob("*.trace.json"),
                     key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
        try:
            doc = json.loads(tp.read_text(encoding="utf-8"))
        except Exception:
            continue
        s = doc.get("stimulus_score")
        if isinstance(s, (int, float)):
            scores.append(float(s))
    if scores:
        return statistics.median(scores[:5])
    # fallback: summary_latest.json
    sl = deep_dir / "summary_latest.json"
    if sl.exists():
        try:
            doc = json.loads(sl.read_text(encoding="utf-8"))
            s = doc.get("stimulus_score")
            if isinstance(s, (int, float)):
                return float(s)
        except Exception:
            pass
    return None


def _load_knee_flag(memory_dir: Path) -> Optional[str]:
    path = memory_dir / "physiology" / "response_profile.json"
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return (doc.get("knee_loading") or {}).get("flag")
    except Exception:
        return None


def _locate_window(
    windows: list[MacroWindow], ref: date
) -> MacroWindow:
    for w in windows:
        if w.start_date <= ref <= w.end_date:
            return w
    # fallback: 最接近的窗口
    return min(windows, key=lambda w: abs((w.start_date - ref).days))


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def refresh_periodization(
    warehouse_dir: Path,
    memory_dir: Path,
    reference_date: date,
    generated_at: str,
) -> dict:
    t0 = time.monotonic()
    warehouse_dir = Path(warehouse_dir)
    memory_dir = Path(memory_dir)

    try:
        wellness = _load_wellness(warehouse_dir)
        athlete = _load_athlete(warehouse_dir)
        baseline_ctl = 90.0
        if wellness:
            last = [w for w in wellness if w.get("ctl") is not None]
            if last:
                baseline_ctl = float(last[-1]["ctl"])

        slope = analyze_ctl_slope(
            wellness, reference_date=reference_date, window_days=28)
        races = load_race_calendar(warehouse_dir, memory_dir)
        nxt = next_race_after(races, reference_date)

        # 90-day peak CTL
        ctl_90d_peak = 0.0
        for w in wellness:
            try:
                d = date.fromisoformat(str(w.get("id", ""))[:10])
            except Exception:
                continue
            if (reference_date - d).days <= 90 and w.get("ctl") is not None:
                ctl_90d_peak = max(ctl_90d_peak, float(w["ctl"]))

        stimulus_median = _load_stimulus_median(memory_dir)
        phase, reasons = detect_phase(
            reference_date=reference_date, ctl_slope=slope, races=races,
            ctl_90d_peak=ctl_90d_peak or baseline_ctl,
            recent_stimulus_median=stimulus_median,
        )

        macro = plan_macro(
            reference_date=reference_date,
            baseline_ctl=baseline_ctl,
            races=races,
            generated_at=generated_at,
        )
        window = _locate_window(macro.windows, reference_date)
        knee = _load_knee_flag(memory_dir)
        pattern = select_meso_pattern(
            phase=window.phase,
            knee_flag=knee,
            recent_atl_delta=0.0,
            response_high_responder=False,
        )
        meso = build_meso_block(
            reference_date=reference_date, macro=window, pattern=pattern)

        intent = build_intent_for_phase(window.phase, baseline_ctl)
        week_monday = _monday_of(reference_date)
        week_idx = max(0, (week_monday - meso.block_start).days // 7)
        micro = build_micro_cycle(
            week_start=week_monday, meso=meso, intent=intent, week_idx=week_idx)

        next_race = None
        if nxt is not None:
            next_race = NextRace(
                name=nxt.name, race_date=nxt.race_date,
                priority=nxt.priority, course_hint=nxt.course_hint,
            )

        snap = PeriodizationSnapshot(
            generated_at=generated_at, current_phase=phase,
            macro=macro, meso=meso, micro=micro, next_race=next_race,
        )
        path = write_periodization_snapshot(
            memory_dir / "periodization", snap)

        LOG.event(
            action="refresh_periodization",
            duration_ms=int((time.monotonic() - t0) * 1000),
            status="ok",
            phase=phase.value,
            reasons_count=len(reasons),
            snapshot_path=path,
        )
        return {"status": "ok", "phase": phase.value,
                "reasons": reasons, "snapshot_path": path}

    except Exception as e:
        LOG.event(
            action="refresh_periodization",
            duration_ms=int((time.monotonic() - t0) * 1000),
            status="error",
            error=str(e),
        )
        return {"status": "error", "error": str(e)}
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_engine.py -v`
Expected: PASS all three.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/engine.py \
        icu/tests/unit/periodization/test_engine.py
git commit -m "feat(coach-phase2): periodization engine facade (detects phase + builds snapshot + JSONL logs)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/periodization/ -v` 全绿（T25–T35 累计）
- [ ] 2 次提交（T34 / T35）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`06-session-designer-infra.md`](./06-session-designer-infra.md) 开始。
