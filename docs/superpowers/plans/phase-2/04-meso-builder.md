# Phase 2 — Meso block builder (Tasks T32–T33)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/periodization/meso_builder.py`
- `icu/tests/unit/periodization/test_meso_builder.py`

**Goal:** 给定当前 `MacroWindow` 和 `baseline_ctl`，产出覆盖 3–6 周的 `MesoBlock`，每周一个负荷乘数。解决的问题：只有 `PhaseIntent` 不够 — 必须把 4 周写成 "1.0 / 1.05 / 1.10 / 0.70"（3:1 pattern），这样每周的 TSS 目标才有层次，最后一周才有显式的 deload。

---

## Task 32: Pattern selector

**Goal:** 根据阶段 + response_profile.knee_loading.flag + ATL 趋势，选一个 pattern 字符串：
- `"3:1"` — 三周累加 + 一周 deload。默认
- `"2:1"` — 高响应用户；更频繁恢复。knee_loading.flag=="caution" 强制回到 3:1 更保守
- `"polarized"` — 仅 BASE 阶段使用，周内极化分配更重要，周间几乎持平
- `"linear"` — TAPER 用，单调下降

Pattern 由一个 `select_meso_pattern()` 函数返回；模板表放在模块常量里。

**Files:**
- Create: `icu/src/coach/periodization/meso_builder.py`（先写 pattern selector + 常量）
- Create: `icu/tests/unit/periodization/test_meso_builder.py`

- [ ] **Step 1: Write failing tests — pattern selection rules**

Write `icu/tests/unit/periodization/test_meso_builder.py`:
```python
from datetime import date
import pytest

from src.coach.periodization.meso_builder import (
    select_meso_pattern, MESO_PATTERNS, build_meso_block,
)
from src.coach.periodization.types import Phase


def test_base_phase_uses_polarized():
    p = select_meso_pattern(
        phase=Phase.BASE, knee_flag=None, recent_atl_delta=0.0)
    assert p == "polarized"


def test_build_default_three_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag=None, recent_atl_delta=2.0)
    assert p == "3:1"


def test_build_high_responder_two_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag=None,
        recent_atl_delta=2.0, response_high_responder=True)
    assert p == "2:1"


def test_knee_caution_forces_three_one_over_two_one():
    p = select_meso_pattern(
        phase=Phase.BUILD, knee_flag="caution",
        recent_atl_delta=2.0, response_high_responder=True)
    assert p == "3:1"


def test_taper_uses_linear():
    p = select_meso_pattern(
        phase=Phase.TAPER, knee_flag=None, recent_atl_delta=-3.0)
    assert p == "linear"


def test_all_patterns_defined():
    assert set(MESO_PATTERNS.keys()) == {"3:1", "2:1", "polarized", "linear"}
    for multipliers in MESO_PATTERNS.values():
        # 3-6 周长度
        assert 3 <= len(multipliers) <= 6
        # deload 周必须 < 1.0，加载周 ≥ 1.0
        assert min(multipliers) < 1.0
        assert max(multipliers) >= 1.0
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 3: Implement pattern selector + table**

Write `icu/src/coach/periodization/meso_builder.py`:
```python
"""Meso 块构造器：pattern 选择 + 周负荷乘数 + 日期窗口。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .types import MesoBlock, Phase

MESO_PATTERNS: dict[str, list[float]] = {
    # 经典 3-week load + 1-week deload
    "3:1": [1.00, 1.05, 1.10, 0.70],
    # 高响应用户：更频繁减量
    "2:1": [1.00, 1.08, 0.65],
    # BASE 极化期：几乎等量、低强度为主
    "polarized": [1.00, 1.00, 1.00, 0.85],
    # TAPER：单调下降
    "linear": [1.00, 0.70, 0.40],
}


def select_meso_pattern(
    phase: Phase,
    knee_flag: Optional[str] = None,
    recent_atl_delta: float = 0.0,
    response_high_responder: bool = False,
) -> str:
    """选择合适的 meso pattern。规则：
    - BASE → polarized
    - TAPER / RACE → linear
    - BUILD / PEAK：高响应者可以 2:1；knee_flag in {'caution','watch'} 强制回 3:1
    - TRANSITION → 沿用 3:1（deload 本身）
    """
    if phase is Phase.BASE:
        return "polarized"
    if phase in (Phase.TAPER, Phase.RACE):
        return "linear"
    if phase in (Phase.BUILD, Phase.PEAK):
        if knee_flag in ("caution", "watch"):
            return "3:1"
        if response_high_responder:
            return "2:1"
        return "3:1"
    # TRANSITION
    return "3:1"
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_meso_builder.py -v`
Expected: PASS all six.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/meso_builder.py \
        icu/tests/unit/periodization/test_meso_builder.py
git commit -m "feat(coach-phase2): meso pattern selector (3:1/2:1/polarized/linear + knee-safety override)"
```

---

## Task 33: Build meso block with dates + load multipliers

**Goal:** 给定当前日期所在的 `MacroWindow` 和选中的 pattern，计算 `MesoBlock`：
- `block_start`: 当前日期所在周的周一，或 macro window 的 start（取较晚者）
- 按 pattern 长度 × 7 天计算 `block_end`；如果 macro window 更早结束，用 macro end 截断
- `weekly_load_multipliers` 直接取 `MESO_PATTERNS[pattern]`（如被截断则对应截掉尾部周）

**Files:**
- Modify: `icu/src/coach/periodization/meso_builder.py`（append `build_meso_block`）
- Modify: `icu/tests/unit/periodization/test_meso_builder.py`（append）

- [ ] **Step 1: Write failing test — block dates & multipliers**

Append to `test_meso_builder.py`:
```python
from src.coach.periodization.types import MacroWindow, PhaseIntent

def _make_macro_window(
    start: date, end: date, phase: Phase = Phase.BUILD
) -> MacroWindow:
    intent = PhaseIntent(
        phase=phase, primary_adaptation="threshold_capacity",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )
    return MacroWindow(phase=phase, start_date=start, end_date=end, intent=intent)


def test_build_meso_block_aligns_to_monday():
    # reference_date = Sat 2026-04-18; its Monday = 2026-04-13
    macro = _make_macro_window(date(2026, 4, 1), date(2026, 5, 28))
    meso = build_meso_block(
        reference_date=date(2026, 4, 18),
        macro=macro, pattern="3:1",
    )
    assert meso.block_start == date(2026, 4, 13)  # Monday
    # 4 周 = 28 天（block_start + 27d）
    assert meso.block_end == date(2026, 4, 13) + timedelta(days=27)
    assert meso.weekly_load_multipliers == [1.00, 1.05, 1.10, 0.70]
    assert meso.phase is Phase.BUILD


def test_build_meso_block_truncates_when_macro_window_ends_sooner():
    # Macro ends in 10 days (well under 4 weeks)
    macro = _make_macro_window(date(2026, 4, 13), date(2026, 4, 22))
    meso = build_meso_block(
        reference_date=date(2026, 4, 13),
        macro=macro, pattern="3:1",
    )
    assert meso.block_end == date(2026, 4, 22)  # truncated
    # Only 2 weeks fit (14 days including both ends close enough);
    # multipliers must be clipped to reflect actual weeks included
    assert 1 <= len(meso.weekly_load_multipliers) <= 2


def test_build_meso_block_taper_linear_three_weeks():
    macro = _make_macro_window(
        date(2026, 5, 1), date(2026, 5, 21), phase=Phase.TAPER
    )
    meso = build_meso_block(
        reference_date=date(2026, 5, 1), macro=macro, pattern="linear",
    )
    # linear pattern has 3 weeks
    assert len(meso.weekly_load_multipliers) == 3
    assert meso.weekly_load_multipliers == [1.00, 0.70, 0.40]


def test_build_meso_block_ignores_unknown_pattern():
    import pytest
    macro = _make_macro_window(date(2026, 4, 1), date(2026, 5, 28))
    with pytest.raises(KeyError):
        build_meso_block(
            reference_date=date(2026, 4, 18),
            macro=macro, pattern="does-not-exist",
        )
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — `build_meso_block` undefined.

- [ ] **Step 3: Implement `build_meso_block`**

Append to `icu/src/coach/periodization/meso_builder.py`:
```python
def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def build_meso_block(
    reference_date: date,
    macro: "MacroWindow",  # forward ref; already imported via types
    pattern: str,
) -> MesoBlock:
    """产出当前 Meso 块。从 reference_date 所在周的周一开始；若 macro 更晚开始，使用 macro.start_date。"""
    from .types import MacroWindow  # 避免循环
    assert isinstance(macro, MacroWindow)
    if pattern not in MESO_PATTERNS:
        raise KeyError(f"unknown meso pattern: {pattern}")
    multipliers = list(MESO_PATTERNS[pattern])

    block_start = max(_monday_of(reference_date), macro.start_date)
    natural_end = block_start + timedelta(days=7 * len(multipliers) - 1)
    if natural_end <= macro.end_date:
        block_end = natural_end
    else:
        # 截断：保留完整周数直到 macro.end_date
        block_end = macro.end_date
        available_days = (block_end - block_start).days + 1
        full_weeks = max(1, (available_days + 6) // 7)  # 向上取整，至少 1 周
        multipliers = multipliers[:full_weeks]
    return MesoBlock(
        pattern=pattern,
        block_start=block_start,
        block_end=block_end,
        weekly_load_multipliers=multipliers,
        phase=macro.phase,
    )
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/periodization/test_meso_builder.py -v`
Expected: PASS all 10 tests.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/periodization/meso_builder.py \
        icu/tests/unit/periodization/test_meso_builder.py
git commit -m "feat(coach-phase2): build_meso_block (Monday-aligned dates + macro-window truncation)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/periodization/ -v` 全绿
- [ ] 2 次提交（T32 / T33）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`05-micro-cycle.md`](./05-micro-cycle.md) 开始。
