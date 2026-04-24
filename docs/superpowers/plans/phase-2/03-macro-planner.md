# Phase 2 — Macro planner (Tasks T30–T31)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/periodization/macro_planner.py`
- `icu/src/coach/periodization/intent_library.py`
- `icu/tests/unit/periodization/test_intent_library.py`
- `icu/tests/unit/periodization/test_macro_planner.py`

**Goal:** 基于赛历（或无赛历的自由训练模式）把赛季/未来 12–24 周切成一串 `MacroWindow`，每个窗口绑定一份来自 `intent_library` 的 `PhaseIntent`。

---

## Task 30: Intent library — per-phase physiological intent templates

**Rationale:** 把"每个阶段该追求什么适应"固化成代码，避免 LLM 每次重新发明。所有模板的强度分配、TSS 目标、休息日数都来自 Allen-Coggan + Seiler + Mujika 的公开协议。

**Files:**
- Create: `icu/src/coach/periodization/intent_library.py`
- Create: `icu/tests/unit/periodization/test_intent_library.py`

### Phase 模板表（实现的 ground truth）

| Phase | primary_adaptation | weekly_tss_target (baseline CTL=90) | low/mid/high | rest_days | 文献依据 |
|---|---|---|---|---|---|
| BASE | `aerobic_base` | `ctl * 5.0` | 85/10/5 | 1 | Seiler 2010 极化，80% low-intensity |
| BUILD | `threshold_capacity` | `ctl * 5.8` | 75/15/10 | 1 | Allen-Coggan 2019 sweet-spot/threshold emphasis |
| PEAK | `vo2_power_sharpening` | `ctl * 5.3` | 65/15/20 | 1–2 | Seiler peak week, 强度比例抬到 20% |
| TAPER | `freshness_preservation` | `ctl * 2.5` | 60/10/30 | 2 | Mujika 2009: vol -50%, intensity preserved |
| RACE | `race_execution` | `ctl * 1.5` | 50/10/40 | 2 | race-week openers only |
| TRANSITION | `active_recovery` | `ctl * 2.8` | 95/5/0 | 3 | off-season; unstructured Z1/Z2 |

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/periodization/test_intent_library.py`:
```python
from src.coach.periodization.intent_library import (
    build_intent_for_phase, INTENT_TEMPLATES,
)
from src.coach.periodization.types import Phase


def test_all_phases_have_template():
    for p in Phase:
        assert p in INTENT_TEMPLATES


def test_build_intent_scales_tss_with_ctl():
    intent_lo = build_intent_for_phase(Phase.BUILD, baseline_ctl=60)
    intent_hi = build_intent_for_phase(Phase.BUILD, baseline_ctl=110)
    assert intent_lo.weekly_tss_target < intent_hi.weekly_tss_target
    # 分配比例应该保持一致
    assert intent_lo.intensity_distribution_pct == intent_hi.intensity_distribution_pct


def test_taper_has_high_intensity_preserved():
    intent = build_intent_for_phase(Phase.TAPER, baseline_ctl=90)
    assert intent.intensity_distribution_pct["high"] >= 25
    # vol: TSS target 应 << BUILD
    build = build_intent_for_phase(Phase.BUILD, baseline_ctl=90)
    assert intent.weekly_tss_target < build.weekly_tss_target * 0.6


def test_base_polarized_distribution():
    intent = build_intent_for_phase(Phase.BASE, baseline_ctl=90)
    assert intent.intensity_distribution_pct["low"] >= 80


def test_rationale_cites_source():
    intent = build_intent_for_phase(Phase.TAPER, baseline_ctl=90)
    assert "Mujika" in intent.rationale or "taper" in intent.rationale.lower()


def test_distribution_always_sums_to_100():
    for p in Phase:
        intent = build_intent_for_phase(p, baseline_ctl=85)
        assert sum(intent.intensity_distribution_pct.values()) == 100


def test_build_intent_respects_minimum_ctl_guard():
    # 极低 CTL 时仍有合理下限
    intent = build_intent_for_phase(Phase.BUILD, baseline_ctl=20)
    assert intent.weekly_tss_target >= 150
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement intent_library**

Write `icu/src/coach/periodization/intent_library.py`:
```python
"""每个 Phase 的生理学意图模板。来源：Allen-Coggan、Seiler、Mujika 公开协议。"""
from __future__ import annotations

from .types import Phase, PhaseIntent

MIN_WEEKLY_TSS = 150


INTENT_TEMPLATES: dict[Phase, dict] = {
    Phase.BASE: {
        "primary_adaptation": "aerobic_base",
        "tss_per_ctl": 5.0,
        "distribution": {"low": 85, "mid": 10, "high": 5},
        "rest_days": 1,
        "rationale": (
            "Seiler 2010 polarized base: ≥80% low-intensity. 目标打底有氧、线粒体密度、"
            "脂肪氧化能力；不追强度。"
        ),
    },
    Phase.BUILD: {
        "primary_adaptation": "threshold_capacity",
        "tss_per_ctl": 5.8,
        "distribution": {"low": 75, "mid": 15, "high": 10},
        "rest_days": 1,
        "rationale": (
            "Allen-Coggan 2019 build block: sweet-spot + threshold 为主，周期性加入 "
            "VO2max 刺激。CTL ramp rate 目标 3–5/周。"
        ),
    },
    Phase.PEAK: {
        "primary_adaptation": "vo2_power_sharpening",
        "tss_per_ctl": 5.3,
        "distribution": {"low": 65, "mid": 15, "high": 20},
        "rest_days": 1,
        "rationale": (
            "Peak block 把高强度占比抬到 20%，短间歇 (3–5min) 反复出现，"
            "同时开始降低总量，为 Taper 铺路。"
        ),
    },
    Phase.TAPER: {
        "primary_adaptation": "freshness_preservation",
        "tss_per_ctl": 2.5,
        "distribution": {"low": 60, "mid": 10, "high": 30},
        "rest_days": 2,
        "rationale": (
            "Mujika 2009 taper meta-analysis: 总量 -41–60%，但保持强度；刺激短而尖。"
            "关键是让 ATL 快速下降、TSB 回到 +5~+15。"
        ),
    },
    Phase.RACE: {
        "primary_adaptation": "race_execution",
        "tss_per_ctl": 1.5,
        "distribution": {"low": 50, "mid": 10, "high": 40},
        "rest_days": 2,
        "rationale": (
            "Race week: openers only。目标是把神经和能量系统唤醒，不做任何产生显著 "
            "TSS 的动作。"
        ),
    },
    Phase.TRANSITION: {
        "primary_adaptation": "active_recovery",
        "tss_per_ctl": 2.8,
        "distribution": {"low": 95, "mid": 5, "high": 0},
        "rest_days": 3,
        "rationale": (
            "Off-season / transition: 2–4 周无结构化训练，降低 CTL、释放累积疲劳、"
            "处理伤病。没有强度，只做 Z1/Z2 户外骑行。"
        ),
    },
}


def build_intent_for_phase(phase: Phase, baseline_ctl: float) -> PhaseIntent:
    tpl = INTENT_TEMPLATES[phase]
    weekly_tss = max(MIN_WEEKLY_TSS, int(round(baseline_ctl * tpl["tss_per_ctl"])))
    return PhaseIntent(
        phase=phase,
        primary_adaptation=tpl["primary_adaptation"],
        weekly_tss_target=weekly_tss,
        intensity_distribution_pct=dict(tpl["distribution"]),
        rest_days_per_week=tpl["rest_days"],
        rationale=tpl["rationale"],
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_intent_library.py -v`
Expected: PASS all seven.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/intent_library.py \
        icu/tests/unit/periodization/test_intent_library.py
git commit -m "feat(coach-phase2): phase intent library (Base/Build/Peak/Taper/Race/Transition templates)"
```

---

## Task 31: Macro planner — season layout backwards from races

**Goal:** 接收 `RaceEntry` 列表 + 当前日期 + baseline CTL，产出 12 个月内的 `MacroPlan`。
算法：
1. 对每个 A 级赛倒推 — 赛前 10 天 Taper，再向前 14 天 Peak，再向前 4 周 Build，再向前 6 周 Base。
2. 两场赛之间的空档若 < 8 周：归为 Maintain (Build/Peak 交替微缩)。
3. 若没有 A 级赛：
   - **baseline_ctl < 75**：整个 12 周当 BASE（底盘保护，用户决策 2026-04-18）。
   - 否则：整个 12 周当 BUILD，每 4 周插入 1 周 Transition。
4. 窗口不重叠（后到的赛前窗口覆盖前面的 Transition/Build 尾部）。

**Files:**
- Create: `icu/src/coach/periodization/macro_planner.py`
- Create: `icu/tests/unit/periodization/test_macro_planner.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/periodization/test_macro_planner.py`:
```python
from datetime import date, timedelta
from src.coach.periodization.macro_planner import plan_macro
from src.coach.periodization.race_calendar import RaceEntry
from src.coach.periodization.types import Phase


def test_single_race_builds_six_windows_backwards():
    race = RaceEntry(name="Goal HC", race_date=date(2026, 6, 14), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 18),
        baseline_ctl=90,
        races=[race],
        generated_at="2026-04-18T00:00:00Z",
    )
    phases = [w.phase for w in plan.windows]
    # 必须包含逆推出的完整链
    assert Phase.TAPER in phases
    assert Phase.PEAK in phases
    assert Phase.BUILD in phases
    assert Phase.BASE in phases
    # 最后一个窗口的 end >= race_date - 1
    last = [w for w in plan.windows if w.phase is Phase.TAPER][-1]
    assert race.race_date - last.end_date <= timedelta(days=1)


def test_no_races_defaults_to_rolling_build_with_transition():
    plan = plan_macro(
        reference_date=date(2026, 1, 5),
        baseline_ctl=80,
        races=[],
        generated_at="2026-01-05T00:00:00Z",
    )
    phases = [w.phase for w in plan.windows]
    assert Phase.BUILD in phases
    # 应该插入至少一次 Transition 微恢复
    assert Phase.TRANSITION in phases


def test_no_races_low_ctl_rolls_out_as_base():
    """底盘保护：baseline_ctl < 75 且无赛 → 全 12 周 BASE。"""
    plan = plan_macro(
        reference_date=date(2026, 1, 5),
        baseline_ctl=68,
        races=[],
        generated_at="2026-01-05T00:00:00Z",
    )
    phases = {w.phase for w in plan.windows}
    assert Phase.BASE in phases
    assert Phase.BUILD not in phases


def test_two_close_races_no_gap_becomes_maintain():
    r1 = RaceEntry(name="Race1", race_date=date(2026, 5, 3), priority="A")
    r2 = RaceEntry(name="Race2", race_date=date(2026, 5, 24), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 1), baseline_ctl=88,
        races=[r1, r2],
        generated_at="2026-04-01T00:00:00Z",
    )
    # 两赛间隔 21 天 < 56 天 → 不再走完整 Base→Build→Peak→Taper；
    # 第二场赛前有一次小 Taper/Peak
    r2_taper = [w for w in plan.windows
                if w.phase is Phase.TAPER and w.end_date <= r2.race_date]
    assert len(r2_taper) >= 1


def test_generated_windows_are_sorted_and_non_overlapping():
    race = RaceEntry(name="A", race_date=date(2026, 6, 14), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 18), baseline_ctl=90,
        races=[race], generated_at="2026-04-18T00:00:00Z",
    )
    starts = [w.start_date for w in plan.windows]
    ends = [w.end_date for w in plan.windows]
    assert starts == sorted(starts)
    # 相邻窗口不重叠（允许 end_n == start_{n+1}）
    for i in range(len(plan.windows) - 1):
        assert plan.windows[i].end_date <= plan.windows[i+1].start_date


def test_every_window_has_intent_with_matching_phase():
    race = RaceEntry(name="A", race_date=date(2026, 6, 14), priority="A")
    plan = plan_macro(
        reference_date=date(2026, 4, 18), baseline_ctl=90,
        races=[race], generated_at="2026-04-18T00:00:00Z",
    )
    for w in plan.windows:
        assert w.intent.phase is w.phase
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement macro_planner**

Write `icu/src/coach/periodization/macro_planner.py`:
```python
"""宏观规划：赛历 → 一串 MacroWindow。倒推算法，详见 03-macro-planner.md T31。"""
from __future__ import annotations

from datetime import date, timedelta

from .intent_library import build_intent_for_phase
from .race_calendar import RaceEntry
from .types import MacroPlan, MacroWindow, Phase

TAPER_DAYS = 10
PEAK_DAYS = 14
BUILD_DAYS = 28
BASE_DAYS = 42
MAINTAIN_MIN_GAP_DAYS = 56
DEFAULT_HORIZON_WEEKS = 12
TRANSITION_EVERY_WEEKS = 4
TRANSITION_LEN_DAYS = 7
CTL_BASE_PROTECT = 75.0  # 与 phase_detector 一致（用户决策 2026-04-18）


def _backwards_from_race(
    race: RaceEntry, baseline_ctl: float
) -> list[MacroWindow]:
    """从一场 A 级赛倒推 Taper → Peak → Build → Base。"""
    r = race.race_date
    taper_start = r - timedelta(days=TAPER_DAYS)
    peak_start = taper_start - timedelta(days=PEAK_DAYS)
    build_start = peak_start - timedelta(days=BUILD_DAYS)
    base_start = build_start - timedelta(days=BASE_DAYS)
    return [
        MacroWindow(phase=Phase.BASE, start_date=base_start,
                    end_date=build_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.BASE, baseline_ctl)),
        MacroWindow(phase=Phase.BUILD, start_date=build_start,
                    end_date=peak_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.BUILD, baseline_ctl)),
        MacroWindow(phase=Phase.PEAK, start_date=peak_start,
                    end_date=taper_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.PEAK, baseline_ctl)),
        MacroWindow(phase=Phase.TAPER, start_date=taper_start,
                    end_date=r - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.TAPER, baseline_ctl)),
    ]


def _maintain_between(
    prev_race: RaceEntry, next_race: RaceEntry, baseline_ctl: float
) -> list[MacroWindow]:
    """两赛间隔短的情况：仅 Peak(缩) + Taper。"""
    gap_days = (next_race.race_date - prev_race.race_date).days
    # 保留前赛后 3 天的微恢复 → 然后 Peak → Taper
    peak_start = prev_race.race_date + timedelta(days=3)
    taper_start = next_race.race_date - timedelta(days=TAPER_DAYS)
    if peak_start >= taper_start:
        # 实在太挤，合并成短 Taper
        return [MacroWindow(
            phase=Phase.TAPER, start_date=peak_start,
            end_date=next_race.race_date - timedelta(days=1),
            intent=build_intent_for_phase(Phase.TAPER, baseline_ctl),
        )]
    return [
        MacroWindow(phase=Phase.PEAK, start_date=peak_start,
                    end_date=taper_start - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.PEAK, baseline_ctl)),
        MacroWindow(phase=Phase.TAPER, start_date=taper_start,
                    end_date=next_race.race_date - timedelta(days=1),
                    intent=build_intent_for_phase(Phase.TAPER, baseline_ctl)),
    ]


def _default_rolling_build(
    reference_date: date, baseline_ctl: float, horizon_weeks: int
) -> list[MacroWindow]:
    """无赛历：根据 baseline_ctl 决定走 BASE 还是 BUILD 循环。

    - CTL < CTL_BASE_PROTECT (75)：整个 horizon 全 BASE（底盘保护）。
    - 否则：每 4 周 BUILD + 1 周 TRANSITION 循环。
    """
    end = reference_date + timedelta(weeks=horizon_weeks)

    if baseline_ctl < CTL_BASE_PROTECT:
        return [MacroWindow(
            phase=Phase.BASE,
            start_date=reference_date,
            end_date=end - timedelta(days=1),
            intent=build_intent_for_phase(Phase.BASE, baseline_ctl),
        )]

    out: list[MacroWindow] = []
    cur = reference_date
    while cur < end:
        b_end = min(cur + timedelta(weeks=TRANSITION_EVERY_WEEKS) - timedelta(days=1),
                    end - timedelta(days=1))
        out.append(MacroWindow(
            phase=Phase.BUILD, start_date=cur, end_date=b_end,
            intent=build_intent_for_phase(Phase.BUILD, baseline_ctl),
        ))
        cur = b_end + timedelta(days=1)
        if cur >= end:
            break
        t_end = min(cur + timedelta(days=TRANSITION_LEN_DAYS - 1),
                    end - timedelta(days=1))
        out.append(MacroWindow(
            phase=Phase.TRANSITION, start_date=cur, end_date=t_end,
            intent=build_intent_for_phase(Phase.TRANSITION, baseline_ctl),
        ))
        cur = t_end + timedelta(days=1)
    return out


def _merge_and_trim(windows: list[MacroWindow]) -> list[MacroWindow]:
    """按 start_date 排序，后者覆盖前者的尾部，保证不重叠。"""
    if not windows:
        return []
    sorted_w = sorted(windows, key=lambda w: w.start_date)
    out: list[MacroWindow] = [sorted_w[0]]
    for w in sorted_w[1:]:
        prev = out[-1]
        if w.start_date <= prev.end_date:
            out[-1] = prev.model_copy(
                update={"end_date": w.start_date - timedelta(days=1)}
            )
            if out[-1].end_date < out[-1].start_date:
                out.pop()
        out.append(w)
    # 丢弃非法窗口
    return [w for w in out if w.end_date >= w.start_date]


def plan_macro(
    reference_date: date,
    baseline_ctl: float,
    races: list[RaceEntry],
    generated_at: str,
) -> MacroPlan:
    a_races = sorted(
        [r for r in races if r.priority.upper() == "A"
         and r.race_date >= reference_date],
        key=lambda r: r.race_date,
    )
    if not a_races:
        windows = _default_rolling_build(
            reference_date, baseline_ctl, DEFAULT_HORIZON_WEEKS
        )
        season_end = (reference_date
                      + timedelta(weeks=DEFAULT_HORIZON_WEEKS))
    else:
        windows: list[MacroWindow] = []
        for idx, race in enumerate(a_races):
            if idx == 0:
                windows.extend(_backwards_from_race(race, baseline_ctl))
            else:
                prev = a_races[idx - 1]
                gap = (race.race_date - prev.race_date).days
                if gap < MAINTAIN_MIN_GAP_DAYS:
                    windows.extend(_maintain_between(prev, race, baseline_ctl))
                else:
                    windows.extend(_backwards_from_race(race, baseline_ctl))
        season_end = a_races[-1].race_date + timedelta(days=7)

    windows = _merge_and_trim([w for w in windows
                               if w.end_date >= reference_date])
    return MacroPlan(
        generated_at=generated_at,
        season_end_date=season_end,
        windows=windows,
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_macro_planner.py -v`
Expected: PASS all five.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/macro_planner.py \
        icu/tests/unit/periodization/test_macro_planner.py
git commit -m "feat(coach-phase2): macro planner (race-calendar-driven backwards season layout)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/periodization/ -v` 全绿
- [ ] 2 次提交完成（T30 / T31）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`04-meso-builder.md`](./04-meso-builder.md) 开始。
