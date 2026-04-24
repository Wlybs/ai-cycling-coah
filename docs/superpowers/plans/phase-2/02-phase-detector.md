# Phase 2 — Phase detector (Tasks T28–T29)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md) for full plan, contracts, and execution rules.

**Files covered:**
- `icu/src/coach/periodization/ctl_slope.py`
- `icu/src/coach/periodization/race_calendar.py`
- `icu/src/coach/periodization/phase_detector.py`
- `icu/tests/unit/periodization/test_ctl_slope.py`
- `icu/tests/unit/periodization/test_race_calendar.py`
- `icu/tests/unit/periodization/test_phase_detector.py`

---

## Task 28: CTL slope analyzer + race calendar loader

### T28.a — CTL slope analyzer

**Goal:** 从 wellness 历史（含每日 CTL）里用**最近 28 天线性回归**估计 CTL 斜率，用于判断当前处于加载期（正斜率）、平台期（接近 0）、恢复期/减量期（负斜率）。

**Files:**
- Create: `icu/src/coach/periodization/ctl_slope.py`
- Create: `icu/tests/unit/periodization/test_ctl_slope.py`

- [ ] **Step 1: Write failing test — known slopes recovered**

Write `icu/tests/unit/periodization/test_ctl_slope.py`:
```python
from datetime import date, timedelta

from src.coach.periodization.ctl_slope import (
    CTLSlope, analyze_ctl_slope,
)


def _series(start: date, values: list[float]) -> list[dict]:
    return [
        {"id": (start + timedelta(days=i)).isoformat(), "ctl": v}
        for i, v in enumerate(values)
    ]


def test_positive_slope_build_load():
    # CTL climbing from 80 → 94 over 28 days
    values = [80 + i * 0.5 for i in range(28)]
    series = _series(date(2026, 3, 22), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert slope.slope_per_day > 0.3
    assert slope.interpretation == "increasing"
    assert slope.sample_size == 28


def test_flat_slope_plateau():
    values = [94.0] * 28
    series = _series(date(2026, 3, 22), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert abs(slope.slope_per_day) < 0.05
    assert slope.interpretation == "flat"


def test_negative_slope_taper():
    values = [100 - i * 0.8 for i in range(28)]
    series = _series(date(2026, 3, 22), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert slope.slope_per_day < -0.3
    assert slope.interpretation == "decreasing"


def test_short_series_fallback_uses_available_days():
    # 只有 10 天数据
    values = [88 + i * 0.4 for i in range(10)]
    series = _series(date(2026, 4, 9), values)
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 18), window_days=28)
    assert slope.sample_size == 10
    # 仍能得出正斜率
    assert slope.slope_per_day > 0.2


def test_missing_ctl_skipped():
    series = [
        {"id": "2026-04-01", "ctl": 90.0},
        {"id": "2026-04-02", "ctl": None},
        {"id": "2026-04-03", "ctl": 91.0},
    ]
    slope = analyze_ctl_slope(series, reference_date=date(2026, 4, 4), window_days=7)
    assert slope.sample_size == 2


def test_empty_series_returns_none_slope():
    slope = analyze_ctl_slope([], reference_date=date(2026, 4, 18), window_days=28)
    assert slope.slope_per_day is None
    assert slope.interpretation == "unknown"
    assert slope.sample_size == 0
```

- [ ] **Step 2: Run — fail**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_ctl_slope.py -v`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement ctl_slope**

Write `icu/src/coach/periodization/ctl_slope.py`:
```python
"""CTL 斜率分析。用 N 天线性回归估计 CTL/d，用于识别加载/平台/减量阶段。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import numpy as np
from pydantic import BaseModel


class CTLSlope(BaseModel):
    slope_per_day: Optional[float]
    interpretation: str  # "increasing" | "flat" | "decreasing" | "unknown"
    sample_size: int
    window_start: Optional[date] = None
    window_end: Optional[date] = None
    last_ctl: Optional[float] = None


def _parse_date(v: str) -> Optional[date]:
    try:
        return datetime.strptime(v[:10], "%Y-%m-%d").date()
    except Exception:
        return None


FLAT_THRESHOLD_PER_DAY = 0.1  # |slope| < 0.1 CTL/d 视为持平


def analyze_ctl_slope(
    wellness_history: list[dict],
    reference_date: date,
    window_days: int = 28,
) -> CTLSlope:
    """从 wellness 列表中按 reference_date 回溯 window_days 做线性拟合。"""
    if not wellness_history:
        return CTLSlope(slope_per_day=None, interpretation="unknown", sample_size=0)

    window_start = reference_date  # 先作占位，稍后被计算出的最早日覆盖
    pairs: list[tuple[date, float]] = []
    for row in wellness_history:
        d = _parse_date(row.get("id", ""))
        ctl = row.get("ctl")
        if d is None or ctl is None:
            continue
        age = (reference_date - d).days
        if 0 <= age < window_days:
            pairs.append((d, float(ctl)))
    if not pairs:
        return CTLSlope(slope_per_day=None, interpretation="unknown", sample_size=0)

    pairs.sort(key=lambda p: p[0])
    xs = np.array([(p[0] - pairs[0][0]).days for p in pairs], dtype=float)
    ys = np.array([p[1] for p in pairs], dtype=float)
    if len(pairs) < 2:
        return CTLSlope(
            slope_per_day=0.0, interpretation="flat", sample_size=1,
            window_start=pairs[0][0], window_end=pairs[0][0],
            last_ctl=pairs[0][1],
        )
    slope, _ = np.polyfit(xs, ys, 1)
    if slope > FLAT_THRESHOLD_PER_DAY:
        interp = "increasing"
    elif slope < -FLAT_THRESHOLD_PER_DAY:
        interp = "decreasing"
    else:
        interp = "flat"
    return CTLSlope(
        slope_per_day=float(slope),
        interpretation=interp,
        sample_size=len(pairs),
        window_start=pairs[0][0],
        window_end=pairs[-1][0],
        last_ctl=pairs[-1][1],
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_ctl_slope.py -v`
Expected: PASS all six.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/ctl_slope.py \
        icu/tests/unit/periodization/test_ctl_slope.py
git commit -m "feat(coach-phase2): CTL slope analyzer (28-day linear fit with interpretation)"
```

### T28.b — Race calendar loader

**Goal:** 合并结构化 `8_Events/events.json`（按 `category == 'RACE'` 或 name 含 `race|比赛|爬坡赛` 等关键词筛选）和可选的手工 `coach_memory/race_calendar.md`。返回按日期升序、去重的 `RaceEntry` 列表。

**Files:**
- Create: `icu/src/coach/periodization/race_calendar.py`
- Create: `icu/tests/unit/periodization/test_race_calendar.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/periodization/test_race_calendar.py`:
```python
from datetime import date
from pathlib import Path

from src.coach.periodization.race_calendar import (
    RaceEntry, load_race_calendar, next_race_after,
)


def test_load_events_filters_race_category(tmp_path):
    events = [
        {"id": 1, "category": "RACE", "name": "Hill Climb 5.26",
         "start_date_local": "2026-05-26T08:00:00"},
        {"id": 2, "category": "WORKOUT", "name": "Endurance",
         "start_date_local": "2026-04-20T09:00:00"},
    ]
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "8_Events" / "events.json").write_text(
        __import__("json").dumps(events, ensure_ascii=False))
    races = load_race_calendar(warehouse_dir=warehouse, memory_dir=tmp_path)
    assert len(races) == 1
    assert races[0].name.startswith("Hill Climb")


def test_keyword_fallback_when_category_missing(tmp_path):
    events = [
        {"id": 99, "name": "Spring 爬坡赛",
         "start_date_local": "2026-05-10T08:00:00"},
    ]
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "8_Events" / "events.json").write_text(
        __import__("json").dumps(events, ensure_ascii=False))
    races = load_race_calendar(warehouse_dir=warehouse, memory_dir=tmp_path)
    assert len(races) == 1
    assert "爬坡" in races[0].name


def test_markdown_fallback_when_events_missing(tmp_path):
    # no events.json
    memory = tmp_path / "coach_memory"
    memory.mkdir()
    (memory / "race_calendar.md").write_text(
        "- 2026-06-15 A 武夷山爬坡赛\n- 2026-07-20 B 环太湖\n",
        encoding="utf-8",
    )
    races = load_race_calendar(warehouse_dir=tmp_path, memory_dir=memory)
    assert len(races) == 2
    assert races[0].priority == "A"
    assert races[1].name.startswith("环太湖")


def test_next_race_after_reference_date():
    races = [
        RaceEntry(name="Past", race_date=date(2026, 3, 1), priority="B"),
        RaceEntry(name="Goal", race_date=date(2026, 5, 26), priority="A"),
        RaceEntry(name="Later", race_date=date(2026, 7, 20), priority="B"),
    ]
    nxt = next_race_after(races, reference_date=date(2026, 4, 18))
    assert nxt.name == "Goal"
    assert nxt.days_out == (date(2026, 5, 26) - date(2026, 4, 18)).days
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement race_calendar**

Write `icu/src/coach/periodization/race_calendar.py`:
```python
"""赛历加载。优先读 8_Events/events.json（RACE 分类或关键词），
回退到 coach_memory/race_calendar.md 简单行格式。"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

RACE_KEYWORDS = ("race", "比赛", "爬坡赛", "赛", "climb")


class RaceEntry(BaseModel):
    name: str
    race_date: date
    priority: str = "A"
    course_hint: Optional[str] = None
    days_out: Optional[int] = None


def _parse_event_date(raw: str) -> Optional[date]:
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _is_race(ev: dict) -> bool:
    cat = str(ev.get("category") or "").upper()
    if cat == "RACE":
        return True
    name = str(ev.get("name") or "").lower()
    return any(kw in name for kw in RACE_KEYWORDS)


_MD_LINE = re.compile(
    r"-\s*(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<pri>[ABC])\s+(?P<name>.+?)\s*$",
    re.IGNORECASE,
)


def _load_from_events(warehouse_dir: Path) -> list[RaceEntry]:
    path = Path(warehouse_dir) / "8_Events" / "events.json"
    if not path.exists():
        return []
    try:
        events = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[RaceEntry] = []
    for ev in events:
        if not _is_race(ev):
            continue
        d = _parse_event_date(str(ev.get("start_date_local", "")))
        if not d:
            continue
        out.append(RaceEntry(
            name=ev.get("name") or "Race",
            race_date=d,
            priority=ev.get("priority") or "A",
            course_hint=ev.get("description"),
        ))
    return out


def _load_from_markdown(memory_dir: Path) -> list[RaceEntry]:
    path = Path(memory_dir) / "race_calendar.md"
    if not path.exists():
        return []
    out: list[RaceEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _MD_LINE.match(line.strip())
        if not m:
            continue
        try:
            d = datetime.strptime(m.group("date"), "%Y-%m-%d").date()
        except ValueError:
            continue
        out.append(RaceEntry(
            name=m.group("name").strip(),
            race_date=d,
            priority=m.group("pri").upper(),
        ))
    return out


def _dedup_sorted(entries: list[RaceEntry]) -> list[RaceEntry]:
    seen: dict[tuple[str, date], RaceEntry] = {}
    for e in entries:
        key = (e.name.strip().lower(), e.race_date)
        seen.setdefault(key, e)
    return sorted(seen.values(), key=lambda e: e.race_date)


def load_race_calendar(
    warehouse_dir: Path, memory_dir: Path
) -> list[RaceEntry]:
    primary = _load_from_events(warehouse_dir)
    if primary:
        return _dedup_sorted(primary)
    return _dedup_sorted(_load_from_markdown(memory_dir))


def next_race_after(
    races: list[RaceEntry], reference_date: date
) -> Optional[RaceEntry]:
    future = [r for r in races if r.race_date >= reference_date]
    if not future:
        return None
    nxt = sorted(future, key=lambda r: r.race_date)[0]
    nxt = nxt.model_copy(update={"days_out": (nxt.race_date - reference_date).days})
    return nxt
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_race_calendar.py -v`
Expected: PASS all four.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/race_calendar.py \
        icu/tests/unit/periodization/test_race_calendar.py
git commit -m "feat(coach-phase2): race calendar loader (events.json primary, race_calendar.md fallback)"
```

---

## Task 29: Combined phase detector

**Goal:** 用 `CTLSlope` + 距下一场目标赛的天数 + 最近 3 次 deep_analysis 的 stimulus_score 组合决策当前阶段。返回一个 `Phase` 和人类可读的 reasons 列表。

**Files:**
- Create: `icu/src/coach/periodization/phase_detector.py`
- Create: `icu/tests/unit/periodization/test_phase_detector.py`

### Phase decision rules（实现必须严格对应以下表格）

规则从上到下匹配，命中即返回。

| # | Scenario | Phase | 主要信号 |
|---|---|---|---|
| 1 | 赛前当日 | `RACE` | days_out == 0 |
| 2 | 距离 A 级赛 ≤ 10 天 | `TAPER` | days_out ∈ (0, 10] |
| 3 | 距离下一 A 级赛 11–21 天 且 `last_ctl` 处于 90 日峰值 95%+ | `PEAK` | days_out ∈ (10, 21], ctl_near_peak |
| 4 | **底盘保护：`last_ctl < 75`** | `BASE` | **CTL 太低，强制先打底，避免底盘未厚就上强度** |
| 5 | CTL 斜率 `decreasing` 且无近期赛 | `TRANSITION` | slope < -0.3 且 no race in 28d |
| 6 | CTL 斜率 `increasing` 且 > 0.2 且 stimulus_score 中位数 > 0.5（或为空） | `BUILD` | loading well, quality on target |
| 7 | CTL 斜率 `flat` 或者 stimulus_score 中位数 < 0.4 | `BASE` | 底盘没打好 / under-prescription |
| 8 | 否则 | `BUILD` | 默认回退（保守） |

> **底盘保护阈值**：`last_ctl < 75` 视为 CTL 偏低，强制 BASE。数值来源：用户决策（2026-04-18）。保护伤病恢复后重返、或长时间未骑的场景。阈值常量 `CTL_BASE_PROTECT` = 75.0。

- [ ] **Step 1: Write failing tests — each row covered**

Write `icu/tests/unit/periodization/test_phase_detector.py`:
```python
from datetime import date

from src.coach.periodization.ctl_slope import CTLSlope
from src.coach.periodization.race_calendar import RaceEntry
from src.coach.periodization.phase_detector import detect_phase
from src.coach.periodization.types import Phase


def _slope(s: float, interp: str, last_ctl: float = 95.0) -> CTLSlope:
    return CTLSlope(slope_per_day=s, interpretation=interp,
                    sample_size=28, last_ctl=last_ctl)


def test_taper_when_race_within_10_days():
    races = [RaceEntry(name="A", race_date=date(2026, 4, 24),
                       priority="A", days_out=6)]
    phase, reasons = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.1, "flat"),
        races=races,
        ctl_90d_peak=96.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.TAPER
    assert any("6 天" in r or "days_out" in r for r in reasons)


def test_race_day():
    races = [RaceEntry(name="A", race_date=date(2026, 4, 18),
                       priority="A", days_out=0)]
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.0, "flat"),
        races=races,
        ctl_90d_peak=96.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.RACE


def test_peak_when_race_11_to_21_days_and_ctl_near_peak():
    races = [RaceEntry(name="A", race_date=date(2026, 5, 7),
                       priority="A", days_out=19)]
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.0, "flat", last_ctl=95.5),
        races=races,
        ctl_90d_peak=96.0,   # last_ctl / peak = 0.9947 > 0.95
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.PEAK


def test_build_when_ctl_increasing_and_quality_on_target():
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.4, "increasing", last_ctl=92.0),
        races=[],
        ctl_90d_peak=92.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.BUILD


def test_base_when_under_prescription_signal():
    phase, reasons = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.05, "flat"),
        races=[],
        ctl_90d_peak=95.0,
        recent_stimulus_median=0.30,  # < 0.4 → BASE
    )
    assert phase is Phase.BASE
    assert any("stimulus" in r for r in reasons)


def test_base_protect_when_ctl_below_75():
    """底盘保护：即使 CTL 在加载、stimulus 正常，CTL<75 一律 BASE。"""
    phase, reasons = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.4, "increasing", last_ctl=70.0),
        races=[],
        ctl_90d_peak=72.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.BASE
    assert any("CTL" in r and "75" in r for r in reasons)


def test_base_protect_ignored_if_race_within_taper_window():
    """赛前 Taper 优先级高于 CTL 保护（临赛不会回 BASE）。"""
    races = [RaceEntry(name="A", race_date=date(2026, 4, 24),
                       priority="A", days_out=6)]
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(0.4, "increasing", last_ctl=70.0),
        races=races,
        ctl_90d_peak=72.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.TAPER


def test_transition_when_ctl_dropping_without_race():
    phase, _ = detect_phase(
        reference_date=date(2026, 4, 18),
        ctl_slope=_slope(-0.5, "decreasing"),
        races=[],
        ctl_90d_peak=95.0,
        recent_stimulus_median=0.55,
    )
    assert phase is Phase.TRANSITION
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement phase_detector**

Write `icu/src/coach/periodization/phase_detector.py`:
```python
"""组合 CTL 斜率 + 赛历 + 最近 stimulus 中位数 → 当前阶段。
决策表详见 02-phase-detector.md 的 Phase decision rules。"""
from __future__ import annotations

from datetime import date
from typing import Optional

from .ctl_slope import CTLSlope
from .race_calendar import RaceEntry, next_race_after
from .types import Phase

TAPER_WINDOW_DAYS = 10
PEAK_MIN_DAYS = 11
PEAK_MAX_DAYS = 21
CTL_NEAR_PEAK_RATIO = 0.95
SLOPE_BUILD_MIN = 0.2
STIMULUS_UNDER = 0.40
CTL_BASE_PROTECT = 75.0  # 底盘保护阈值（用户决策 2026-04-18）


def _next_a_race(races: list[RaceEntry], ref: date) -> Optional[RaceEntry]:
    a_races = [r for r in races if r.priority.upper() == "A"]
    nxt = next_race_after(a_races, ref)
    if nxt is None:
        return next_race_after(races, ref)
    return nxt


def detect_phase(
    reference_date: date,
    ctl_slope: CTLSlope,
    races: list[RaceEntry],
    ctl_90d_peak: Optional[float],
    recent_stimulus_median: Optional[float],
) -> tuple[Phase, list[str]]:
    """返回 (Phase, reasons)。reasons 供 phase_current.json 记录。"""
    reasons: list[str] = []
    nxt = _next_a_race(races, reference_date)
    days_out = nxt.days_out if nxt else None

    # 1. TAPER / RACE
    if days_out is not None:
        if days_out == 0:
            reasons.append(f"race day: {nxt.name}")
            return Phase.RACE, reasons
        if 0 < days_out <= TAPER_WINDOW_DAYS:
            reasons.append(
                f"A-race in {days_out} 天 ({nxt.name}) → TAPER"
            )
            return Phase.TAPER, reasons

    # 2. PEAK — 11–21 天内有 A 赛且 CTL 已在高位
    if (days_out is not None
            and PEAK_MIN_DAYS <= days_out <= PEAK_MAX_DAYS
            and ctl_slope.last_ctl is not None
            and ctl_90d_peak
            and ctl_90d_peak > 0
            and ctl_slope.last_ctl / ctl_90d_peak >= CTL_NEAR_PEAK_RATIO):
        reasons.append(
            f"A-race in {days_out} 天 + CTL at "
            f"{ctl_slope.last_ctl:.1f}/{ctl_90d_peak:.1f} "
            f"(>{int(CTL_NEAR_PEAK_RATIO*100)}% of 90d peak) → PEAK"
        )
        return Phase.PEAK, reasons

    # 2.5. BASE PROTECT — CTL 过低，强制 BASE（但若已被 TAPER/RACE/PEAK 命中则早已 return）
    if (ctl_slope.last_ctl is not None
            and ctl_slope.last_ctl < CTL_BASE_PROTECT):
        reasons.append(
            f"CTL {ctl_slope.last_ctl:.1f} < {CTL_BASE_PROTECT:.0f} "
            f"→ BASE (底盘保护：CTL 偏低，先打有氧底再上强度)"
        )
        return Phase.BASE, reasons

    # 3. TRANSITION — CTL 下降且未来 28 天没有赛
    future_28d = [r for r in races
                  if 0 <= (r.race_date - reference_date).days <= 28]
    if (ctl_slope.interpretation == "decreasing"
            and ctl_slope.slope_per_day is not None
            and ctl_slope.slope_per_day < -0.3
            and not future_28d):
        reasons.append(
            f"CTL slope {ctl_slope.slope_per_day:+.2f}/d, no race within 28d → TRANSITION"
        )
        return Phase.TRANSITION, reasons

    # 4. BASE — under-prescription
    if (recent_stimulus_median is not None
            and recent_stimulus_median < STIMULUS_UNDER):
        reasons.append(
            f"recent stimulus median {recent_stimulus_median:.2f} "
            f"< {STIMULUS_UNDER} → BASE (under-prescribed, need more volume)"
        )
        return Phase.BASE, reasons

    # 5. BUILD — 加载中、质量达标
    if (ctl_slope.slope_per_day is not None
            and ctl_slope.slope_per_day >= SLOPE_BUILD_MIN
            and (recent_stimulus_median is None
                 or recent_stimulus_median >= 0.45)):
        reasons.append(
            f"CTL rising {ctl_slope.slope_per_day:+.2f}/d, quality on target → BUILD"
        )
        return Phase.BUILD, reasons

    # 6. 默认 BUILD（最保守非减量）
    reasons.append("fallback: no strong signal → BUILD (default)")
    return Phase.BUILD, reasons
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_phase_detector.py -v`
Expected: PASS all six.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/phase_detector.py \
        icu/tests/unit/periodization/test_phase_detector.py
git commit -m "feat(coach-phase2): phase detector (CTL slope + race calendar + stimulus composite rule)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/periodization/ -v` 全绿（覆盖 T25–T29）
- [ ] 3 次提交完成（T28.a / T28.b / T29 各一次，或合并为 2 次也可）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`03-macro-planner.md`](./03-macro-planner.md) 开始。
