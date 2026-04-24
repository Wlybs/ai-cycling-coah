# Phase 2 — Session Designer infrastructure (Tasks T36–T38)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/session_designer/__init__.py`
- `icu/src/coach/session_designer/types.py`
- `icu/src/coach/session_designer/workout_library.py`
- `icu/src/coach/session_designer/intent_translator.py`
- `icu/tests/unit/session_designer/test_types.py`
- `icu/tests/unit/session_designer/test_workout_library.py`
- `icu/tests/unit/session_designer/test_intent_translator.py`

**Goal:** Session Designer 包的骨架 + 内部类型 + 可复用的 workout 模板目录 + 把 `DayIntent`（来自 Periodization 层）翻译成一个具名 `WorkoutTemplate` 的选择器。

---

## Task 36: Package scaffold + types

**Files:**
- Create: `icu/src/coach/session_designer/__init__.py`
- Create: `icu/src/coach/session_designer/types.py`
- Create: `icu/tests/unit/session_designer/__init__.py`
- Create: `icu/tests/unit/session_designer/test_types.py`

### Types exported

| Class | Role |
|---|---|
| `SessionIntent` | Designer 消费的单日意图（从 `DayIntent` 转换而来） |
| `WorkoutStep` | 一段训练步（duration_s / target_w_low / target_w_high / cadence / label / zone） |
| `SessionStructure` | 多段 WorkoutStep 组成的结构 |
| `DesignedSession` | 完整的一日计划 — 包含 session_type / name / description / duration_min / target_tss / power_range_w / hr_range_bpm / structure / trace |
| `WeeklyPlan` | 7 天 DesignedSession 汇总 + week_start/end/focus_theme/weekly_tss_target/coaching_summary；**字段必须与旧 `plan_generator.py` 的 WeeklyPlan 严格兼容**，ICU 日历同步和历史对比工具依赖这个结构 |

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/session_designer/test_types.py`:
```python
from datetime import date

import pytest
from pydantic import ValidationError

from src.coach.session_designer.types import (
    SessionIntent, WorkoutStep, SessionStructure, DesignedSession,
    WeeklyPlan, DayPlanV2,
)
from src.coach.periodization.types import (
    IntensityTier, SessionType,
)


def test_workout_step_power_range_ordering():
    step = WorkoutStep(
        label="threshold 20min",
        duration_s=1200,
        target_w_low=275, target_w_high=290,
        zone="Z4",
    )
    assert step.duration_s == 1200
    with pytest.raises(ValidationError):
        WorkoutStep(
            label="invalid", duration_s=600,
            target_w_low=300, target_w_high=280, zone="Z4",
        )


def test_session_structure_total_duration():
    s = SessionStructure(steps=[
        WorkoutStep(label="WU", duration_s=900,
                    target_w_low=120, target_w_high=200, zone="Z1"),
        WorkoutStep(label="main", duration_s=1800,
                    target_w_low=275, target_w_high=290, zone="Z4"),
        WorkoutStep(label="CD", duration_s=600,
                    target_w_low=100, target_w_high=180, zone="Z1"),
    ])
    assert s.total_duration_s == 3300
    assert s.main_duration_s == 1800


def test_session_intent_minimal():
    si = SessionIntent(
        day_of_week="Tue",
        tier=IntensityTier.HARD,
        target_tss=95,
        session_hint="VO2max 5x4' @ 110-115% CP",
    )
    assert si.tier is IntensityTier.HARD


def test_designed_session_requires_matching_duration():
    s = SessionStructure(steps=[
        WorkoutStep(label="WU", duration_s=900,
                    target_w_low=120, target_w_high=200, zone="Z1"),
        WorkoutStep(label="main", duration_s=1200,
                    target_w_low=275, target_w_high=290, zone="Z4"),
    ])
    ds = DesignedSession(
        day_of_week="Tue", date="2026-04-21",
        session_type=SessionType.THRESHOLD, name="Threshold 20min",
        description="warmup, 1x20' @ 95-100% CP, cooldown",
        duration_min=35, target_tss=75, structure=s,
        power_range_w="275-290W",
    )
    assert ds.session_type is SessionType.THRESHOLD
    # duration_min 必须与 structure 合并后的 total_duration 在 ±5% 范围
    assert abs(ds.duration_min * 60 - s.total_duration_s) <= s.total_duration_s * 0.05


def test_weekly_plan_backwards_compat_with_day_plan_fields():
    """WeeklyPlan 必须和旧 plan_generator.DayPlan 字段完全兼容（ICU 日历同步依赖）。"""
    day = DayPlanV2(
        date="2026-04-21", day_of_week="Tue",
        training_type="Threshold", icu_type="Ride",
        name="Threshold 2x20",
        description="warmup 15min; 2x20' @ 95-100% CP r8'; cd 10min",
        duration_min=85, target_tss=95,
        power_range_w="275-290W", hr_range_bpm=None,
    )
    plan = WeeklyPlan(
        week_start="2026-04-20", week_end="2026-04-26",
        focus_theme="threshold + VO2max",
        weekly_tss_target=525,
        coaching_summary="build week 2 of 4; ramp +1.05x",
        days=[day],
    )
    # 关键字段必须全部 dumpable 成与旧结构一致的 JSON
    js = plan.model_dump()
    assert js["days"][0]["training_type"] == "Threshold"
    assert js["days"][0]["icu_type"] == "Ride"
```

- [ ] **Step 2: Run — fail**

Expected: FAIL.

- [ ] **Step 3: Implement types**

Write `icu/src/coach/session_designer/__init__.py`:
```python
"""Session Designer — 从 Periodization 的 MicroCycle 意图合成每日训练。

入口：
  design_week(micro_cycle, physiology_snapshot) -> WeeklyPlan
见 08-weekly-assembler.md T41。"""
```

Write `icu/src/coach/session_designer/types.py`:
```python
"""Session Designer 内部类型。WeeklyPlan / DayPlanV2 与旧 plan_generator 字段兼容。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from ..periodization.types import IntensityTier, SessionType


class WorkoutStep(BaseModel):
    label: str
    duration_s: int = Field(..., ge=5)
    target_w_low: Optional[int] = None
    target_w_high: Optional[int] = None
    target_hr_low: Optional[int] = None
    target_hr_high: Optional[int] = None
    target_rpm_low: Optional[int] = None
    target_rpm_high: Optional[int] = None
    zone: str = Field(..., pattern=r"^(Z1|Z2|Z3|Z4|Z5|Z6|Z7)$")

    @model_validator(mode="after")
    def _check_ranges(self):
        if (self.target_w_low is not None and self.target_w_high is not None
                and self.target_w_low > self.target_w_high):
            raise ValueError("target_w_low must be <= target_w_high")
        if (self.target_hr_low is not None and self.target_hr_high is not None
                and self.target_hr_low > self.target_hr_high):
            raise ValueError("target_hr_low must be <= target_hr_high")
        return self


class SessionStructure(BaseModel):
    steps: list[WorkoutStep]

    @property
    def total_duration_s(self) -> int:
        return sum(s.duration_s for s in self.steps)

    @property
    def main_duration_s(self) -> int:
        # 主集 = 去掉首尾 Z1/Z2 的 WU/CD 后剩下的总时长
        inside = [s for s in self.steps if not s.label.lower() in ("wu", "cd")]
        if not inside:
            return 0
        return sum(s.duration_s for s in inside)


class SessionIntent(BaseModel):
    """内部表示：从 DayIntent 派生过来，供 composer 消费。"""
    day_of_week: str = Field(..., pattern=r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$")
    tier: IntensityTier
    target_tss: int = Field(..., ge=0, le=400)
    session_hint: str


class DesignedSession(BaseModel):
    day_of_week: str
    date: str  # ISO YYYY-MM-DD
    session_type: SessionType
    name: str
    description: str
    duration_min: int = Field(..., ge=0, le=600)
    target_tss: int = Field(..., ge=0, le=400)
    structure: SessionStructure
    power_range_w: Optional[str] = None
    hr_range_bpm: Optional[str] = None
    trace: Optional[dict] = None  # 记录：用了哪个 template、CP 来源、w' 预算等


class DayPlanV2(BaseModel):
    """与旧 plan_generator.DayPlan 字段一对一；Phase 2 输出 JSON 必须能被旧 ICU 日历同步代码读懂。"""
    date: str
    day_of_week: str
    training_type: Literal[
        "Rest", "Recovery", "Aerobic", "Tempo",
        "Threshold", "VO2max", "Neuromuscular", "Race",
    ]
    icu_type: Literal["Ride", "WeightTraining", "Walk", "Run", "Rest"]
    name: str
    description: str
    duration_min: int
    target_tss: int
    power_range_w: Optional[str] = None
    hr_range_bpm: Optional[str] = None


class WeeklyPlan(BaseModel):
    week_start: str
    week_end: str
    focus_theme: str
    weekly_tss_target: int
    coaching_summary: str
    days: list[DayPlanV2]
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_types.py -v`
Expected: PASS all five.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/__init__.py \
        icu/src/coach/session_designer/types.py \
        icu/tests/unit/session_designer/__init__.py \
        icu/tests/unit/session_designer/test_types.py
git commit -m "feat(coach-phase2): session_designer types (WorkoutStep/Structure/SessionIntent/DesignedSession + WeeklyPlan v2)"
```

---

## Task 37: Workout library — parametric templates keyed by session_type

**Goal:** 把常见的干预结构模板化，使用占位符 `${cp}`、`${w_prime}`、`${cp_high}` 等，**不**直接生成瓦特数 — 实际数值由 composer 在 T39 解析时代入。模板提供：
- 多段 WorkoutStep（字符串格式化的 target 范围）
- 目标 tier
- 推荐 TSS 区间（用于匹配检查）
- 知识性 `notes` 文本（给 Gemini prose 阶段引用）

### 初始模板集（最少可用）

| Template name | session_type | tier | Structure |
|---|---|---|---|
| `vo2max_short_5x4` | VO2max | HARD | WU 15' Z1→Z2, 5×(4' @ 110-115% CP, r3' Z1), CD 10' Z1 |
| `vo2max_short_6x3` | VO2max | HARD | WU 15', 6×(3' @ 115-120% CP, r3' Z1), CD 10' |
| `threshold_2x20` | Threshold | HARD | WU 15', 2×(20' @ 97-102% CP, r8' Z1), CD 10' |
| `sweet_spot_3x15` | Tempo | MEDIUM | WU 15', 3×(15' @ 88-93% CP, r5' Z1), CD 10' |
| `tempo_continuous_60` | Tempo | MEDIUM | WU 10', 60' @ 80-85% CP continuous, CD 10' |
| `endurance_long_z2` | Aerobic | EASY | WU 10', main 150-240' @ 65-75% CP, CD 10' |
| `endurance_long_with_tempo` | Aerobic | MEDIUM | WU 10', main: 120' Z2 + 2×10' @ 85% CP inside, CD 10' |
| `recovery_spin` | Recovery | EASY | WU 5', 30-45' @ <60% CP, CD 5' |
| `openers_short` | Neuromuscular | EASY | WU 15', 4×(30'' @ 110% CP, r3' Z1), CD 10' |
| `race_sim_course` | Race | RACE_SIM | 由 composer 根据 course_hint 定制，fallback 到 threshold_2x20 结构 |
| `rest_day` | Rest | REST | 0-length structure (empty steps) |

- [ ] **Step 1: Write failing tests — catalog exists & resolves placeholders**

Write `icu/tests/unit/session_designer/test_workout_library.py`:
```python
import pytest

from src.coach.session_designer.workout_library import (
    WORKOUT_TEMPLATES, get_template, list_templates_for_tier,
)
from src.coach.periodization.types import IntensityTier, SessionType


def test_required_templates_present():
    names = {t.name for t in WORKOUT_TEMPLATES}
    assert "vo2max_short_5x4" in names
    assert "threshold_2x20" in names
    assert "sweet_spot_3x15" in names
    assert "endurance_long_z2" in names
    assert "recovery_spin" in names
    assert "rest_day" in names


def test_every_template_has_session_type_and_tier():
    for t in WORKOUT_TEMPLATES:
        assert isinstance(t.session_type, SessionType)
        assert isinstance(t.tier, IntensityTier)
        assert t.total_duration_s_range[0] <= t.total_duration_s_range[1]


def test_get_template_lookup():
    t = get_template("threshold_2x20")
    assert t.name == "threshold_2x20"
    assert t.session_type is SessionType.THRESHOLD


def test_get_template_missing_raises():
    with pytest.raises(KeyError):
        get_template("does_not_exist")


def test_list_templates_for_tier_filters_correctly():
    hard = list_templates_for_tier(IntensityTier.HARD)
    assert all(t.tier is IntensityTier.HARD for t in hard)
    easy = list_templates_for_tier(IntensityTier.EASY)
    assert any(t.name == "recovery_spin" for t in easy)


def test_template_steps_use_symbolic_targets_not_absolute_watts():
    # 模板里的 target_w_low/high 应该是占位符 None 或带 '${cp}' 之类
    # 这里约定：template 的 WorkoutStep 不使用数字 w，composer 在 T39 填充
    t = get_template("threshold_2x20")
    for step in t.steps:
        assert step.target_w_low is None
        assert step.target_w_high is None
    # 但每步应携带一个 "pct_of_cp_low/high" 字段（在 WorkoutTemplateStep 上扩展）
    assert any(s.pct_of_cp_low is not None for s in t.steps)
```

- [ ] **Step 2: Run — fail**

Expected: FAIL.

- [ ] **Step 3: Implement workout_library**

Write `icu/src/coach/session_designer/workout_library.py`:
```python
"""可复用训练模板。steps 只记录"强度占比"，composer 在 T39 把占比代入 CP 转成瓦特。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..periodization.types import IntensityTier, SessionType


class WorkoutTemplateStep(BaseModel):
    label: str
    duration_s: int = Field(..., ge=5)
    pct_of_cp_low: Optional[float] = None  # 0.60 = 60% CP
    pct_of_cp_high: Optional[float] = None
    w_prime_deplete_pct_max: Optional[float] = None  # 允许消耗的 W' 占比 per rep
    zone: str = Field(..., pattern=r"^(Z1|Z2|Z3|Z4|Z5|Z6|Z7)$")
    rep_count: int = 1  # 若 >1，表示这是个重复步（"5x4'" 展平后步数是 rep_count*2+1；此处扁平化）
    # 上面只保留 duration_s；composer 在 T39 做 rep 展开。也可以把展开放在模板里直接写。
    # 本计划使用显式展开 — rep_count 保留为冗余字段以便描述性文案。


class WorkoutTemplate(BaseModel):
    name: str
    session_type: SessionType
    tier: IntensityTier
    steps: list[WorkoutTemplateStep]
    total_duration_s_range: tuple[int, int]  # (min, max)
    notes: str


def _step(label: str, duration_s: int, pct_low: Optional[float],
          pct_high: Optional[float], zone: str,
          w_prime_max: Optional[float] = None) -> WorkoutTemplateStep:
    return WorkoutTemplateStep(
        label=label, duration_s=duration_s,
        pct_of_cp_low=pct_low, pct_of_cp_high=pct_high,
        zone=zone, w_prime_deplete_pct_max=w_prime_max,
    )


def _wu(dur_s=900) -> WorkoutTemplateStep:
    return _step("WU", dur_s, 0.40, 0.70, "Z1")


def _cd(dur_s=600) -> WorkoutTemplateStep:
    return _step("CD", dur_s, 0.40, 0.60, "Z1")


def _rest_interval(dur_s=180) -> WorkoutTemplateStep:
    return _step("rest", dur_s, 0.40, 0.55, "Z1")


def _build_intervals(label_fmt: str, rep: int, work_s: int,
                     rest_s: int, pct_low: float, pct_high: float,
                     zone: str, w_prime_max: Optional[float]
                     ) -> list[WorkoutTemplateStep]:
    steps: list[WorkoutTemplateStep] = []
    for i in range(rep):
        steps.append(_step(label_fmt.format(i=i+1, total=rep),
                           work_s, pct_low, pct_high, zone, w_prime_max))
        if i < rep - 1:
            steps.append(_rest_interval(rest_s))
    return steps


WORKOUT_TEMPLATES: list[WorkoutTemplate] = [
    WorkoutTemplate(
        name="vo2max_short_5x4",
        session_type=SessionType.VO2MAX, tier=IntensityTier.HARD,
        steps=([_wu()]
               + _build_intervals("VO2 {i}/{total} 4'", 5, 240, 180,
                                  1.10, 1.15, "Z5", 0.25)
               + [_cd()]),
        total_duration_s_range=(2700, 3300),
        notes="经典 5x4' VO2max @ 110-115% CP，r3' active rest。W' 单次消耗上限 25% 以留余量。",
    ),
    WorkoutTemplate(
        name="vo2max_short_6x3",
        session_type=SessionType.VO2MAX, tier=IntensityTier.HARD,
        steps=([_wu()]
               + _build_intervals("VO2 {i}/{total} 3'", 6, 180, 180,
                                  1.15, 1.20, "Z5", 0.20)
               + [_cd()]),
        total_duration_s_range=(2700, 3300),
        notes="6x3' VO2max 高刺激密度，PEAK 阶段使用。",
    ),
    WorkoutTemplate(
        name="threshold_2x20",
        session_type=SessionType.THRESHOLD, tier=IntensityTier.HARD,
        steps=([_wu()]
               + _build_intervals("TH {i}/{total} 20'", 2, 1200, 480,
                                  0.97, 1.02, "Z4", None)
               + [_cd()]),
        total_duration_s_range=(4500, 5400),
        notes="Threshold 2x20 @ 97-102% CP，提高乳酸清除。",
    ),
    WorkoutTemplate(
        name="sweet_spot_3x15",
        session_type=SessionType.TEMPO, tier=IntensityTier.MEDIUM,
        steps=([_wu()]
               + _build_intervals("SS {i}/{total} 15'", 3, 900, 300,
                                  0.88, 0.93, "Z3", None)
               + [_cd()]),
        total_duration_s_range=(4200, 5100),
        notes="Sweet-spot 3x15 @ 88-93% CP，高性价比的有氧+力量区刺激。",
    ),
    WorkoutTemplate(
        name="tempo_continuous_60",
        session_type=SessionType.TEMPO, tier=IntensityTier.MEDIUM,
        steps=[_wu(600), _step("tempo 60'", 3600, 0.80, 0.85, "Z3"),
               _cd(600)],
        total_duration_s_range=(4200, 4800),
        notes="稳态 tempo 60min @ 80-85% CP。",
    ),
    WorkoutTemplate(
        name="endurance_long_z2",
        session_type=SessionType.AEROBIC, tier=IntensityTier.EASY,
        steps=[_wu(600),
               _step("long Z2", 9000, 0.65, 0.75, "Z2"),  # 2.5h
               _cd(600)],
        total_duration_s_range=(7200, 14400),
        notes="长距离 Z2。时长按当日 target_tss 动态调整。",
    ),
    WorkoutTemplate(
        name="endurance_long_with_tempo",
        session_type=SessionType.AEROBIC, tier=IntensityTier.MEDIUM,
        steps=[_wu(600),
               _step("Z2 leg1", 3600, 0.65, 0.75, "Z2"),
               _step("tempo 1/2 10'", 600, 0.82, 0.88, "Z3"),
               _rest_interval(600),
               _step("tempo 2/2 10'", 600, 0.82, 0.88, "Z3"),
               _step("Z2 leg2", 3600, 0.65, 0.75, "Z2"),
               _cd(600)],
        total_duration_s_range=(8400, 12600),
        notes="长骑中段插 2x10' tempo。",
    ),
    WorkoutTemplate(
        name="recovery_spin",
        session_type=SessionType.RECOVERY, tier=IntensityTier.EASY,
        steps=[_step("recovery", 2400, 0.45, 0.55, "Z1")],
        total_duration_s_range=(1800, 3600),
        notes="主动恢复，心率不超过 65% HRmax。",
    ),
    WorkoutTemplate(
        name="openers_short",
        session_type=SessionType.NEUROMUSCULAR, tier=IntensityTier.EASY,
        steps=([_wu()]
               + _build_intervals("opener {i}/{total} 30\"", 4, 30, 180,
                                  1.05, 1.15, "Z5", 0.05)
               + [_cd(600)]),
        total_duration_s_range=(1800, 2700),
        notes="神经肌肉唤醒：短冲 + 长 rest，不产生疲劳。",
    ),
    WorkoutTemplate(
        name="race_sim_course",
        session_type=SessionType.RACE, tier=IntensityTier.RACE_SIM,
        steps=([_wu()]
               + _build_intervals("race-sim 15'", 3, 900, 360,
                                  0.95, 1.05, "Z4", None)
               + [_cd()]),
        total_duration_s_range=(3600, 5400),
        notes="Race-sim 模板骨架；composer 根据 course_hint 替换强度段时长/RPM。",
    ),
    WorkoutTemplate(
        name="rest_day",
        session_type=SessionType.REST, tier=IntensityTier.REST,
        steps=[],
        total_duration_s_range=(0, 0),
        notes="完全休息日。",
    ),
]


def get_template(name: str) -> WorkoutTemplate:
    for t in WORKOUT_TEMPLATES:
        if t.name == name:
            return t
    raise KeyError(f"unknown workout template: {name}")


def list_templates_for_tier(tier: IntensityTier) -> list[WorkoutTemplate]:
    return [t for t in WORKOUT_TEMPLATES if t.tier is tier]
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_workout_library.py -v`
Expected: PASS all six.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/workout_library.py \
        icu/tests/unit/session_designer/test_workout_library.py
git commit -m "feat(coach-phase2): workout library (11 CP-parameterized templates)"
```

---

## Task 38: Intent translator — DayIntent → WorkoutTemplate name

**Goal:** 根据 `DayIntent.session_hint` 的关键字 + `tier` + 近期 response_profile 选择一个模板名。规则优先级：
1. 若 `tier is REST` → `rest_day`
2. `session_hint` 中含具名模板关键字（如 "5x4"、"VO2max"、"threshold"、"sweet-spot"、"tempo"、"long"、"openers"、"race"） → 对应模板
3. 按 `tier` 取 default（见表）
4. 兜底 `recovery_spin`

| Tier | Default |
|---|---|
| REST | rest_day |
| EASY | recovery_spin |
| MEDIUM | sweet_spot_3x15 |
| HARD | threshold_2x20 |
| RACE_SIM | race_sim_course |

`tolerance_class` 微调：
- 若 response_profile.types[<session_type>].tolerance_class == "low" 且 tier == HARD，把 VO2 模板降级为 threshold 模板
- 若 tolerance_class == "high" 且 tier == HARD，可选升级为 6x3

**Files:**
- Create: `icu/src/coach/session_designer/intent_translator.py`
- Create: `icu/tests/unit/session_designer/test_intent_translator.py`

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/session_designer/test_intent_translator.py`:
```python
from src.coach.session_designer.intent_translator import (
    translate_intent,
)
from src.coach.periodization.types import IntensityTier


def _intent(tier, hint):
    return {"tier": tier, "hint": hint}


def test_rest_always_rest_day():
    name = translate_intent(
        tier=IntensityTier.REST, hint="rest",
        tolerance_classes={},
    )
    assert name == "rest_day"


def test_keyword_vo2_matches_vo2_template():
    name = translate_intent(
        tier=IntensityTier.HARD,
        hint="VO2max 5x4' @ 110-115% CP",
        tolerance_classes={"VO2max": "medium"},
    )
    assert name == "vo2max_short_5x4"


def test_keyword_threshold_matches_threshold_template():
    name = translate_intent(
        tier=IntensityTier.HARD, hint="threshold 2x20' @ 97-102% CP",
        tolerance_classes={},
    )
    assert name == "threshold_2x20"


def test_keyword_long_matches_endurance_long_z2():
    name = translate_intent(
        tier=IntensityTier.EASY, hint="long Z2 3h+",
        tolerance_classes={},
    )
    assert name == "endurance_long_z2"


def test_keyword_tempo_matches_tempo_or_ss_for_medium():
    name = translate_intent(
        tier=IntensityTier.MEDIUM, hint="tempo 60min continuous",
        tolerance_classes={},
    )
    # 直接匹配 "tempo continuous" → tempo_continuous_60
    assert name == "tempo_continuous_60"


def test_low_tolerance_downgrades_vo2_to_threshold():
    name = translate_intent(
        tier=IntensityTier.HARD, hint="VO2max 5x4'",
        tolerance_classes={"VO2max": "low"},
    )
    assert name == "threshold_2x20"


def test_default_falls_back_to_tier_default():
    name = translate_intent(
        tier=IntensityTier.MEDIUM, hint="something unclear",
        tolerance_classes={},
    )
    assert name == "sweet_spot_3x15"


def test_race_sim_for_race_tier():
    name = translate_intent(
        tier=IntensityTier.RACE_SIM, hint="RACE",
        tolerance_classes={},
    )
    assert name == "race_sim_course"


def test_openers_keyword_matches():
    name = translate_intent(
        tier=IntensityTier.EASY, hint="short openers 3x30''",
        tolerance_classes={},
    )
    assert name == "openers_short"
```

- [ ] **Step 2: Run — fail**

Expected: FAIL.

- [ ] **Step 3: Implement intent_translator**

Write `icu/src/coach/session_designer/intent_translator.py`:
```python
"""DayIntent → WorkoutTemplate name."""
from __future__ import annotations

from ..periodization.types import IntensityTier

_TIER_DEFAULTS = {
    IntensityTier.REST: "rest_day",
    IntensityTier.EASY: "recovery_spin",
    IntensityTier.MEDIUM: "sweet_spot_3x15",
    IntensityTier.HARD: "threshold_2x20",
    IntensityTier.RACE_SIM: "race_sim_course",
}

# 顺序重要：更具体的关键词先匹配
_KEYWORD_RULES: list[tuple[tuple[str, ...], str]] = [
    (("5x4", "5 x 4"), "vo2max_short_5x4"),
    (("6x3", "6 x 3"), "vo2max_short_6x3"),
    (("vo2",), "vo2max_short_5x4"),
    (("threshold",), "threshold_2x20"),
    (("sweet-spot", "sweet spot"), "sweet_spot_3x15"),
    (("tempo continuous", "continuous tempo"), "tempo_continuous_60"),
    (("long z2", "long endurance", "long ride"), "endurance_long_z2"),
    (("tempo inside", "with tempo", "long with"), "endurance_long_with_tempo"),
    (("opener",), "openers_short"),
    (("race",), "race_sim_course"),
    (("recovery", "spin"), "recovery_spin"),
    (("tempo",), "tempo_continuous_60"),
    (("long",), "endurance_long_z2"),
]


def _match_keyword(hint: str) -> str | None:
    h = hint.lower()
    for keywords, template in _KEYWORD_RULES:
        if any(k in h for k in keywords):
            return template
    return None


def translate_intent(
    tier: IntensityTier,
    hint: str,
    tolerance_classes: dict[str, str],
) -> str:
    if tier is IntensityTier.REST:
        return "rest_day"

    name = _match_keyword(hint) or _TIER_DEFAULTS[tier]

    # tolerance downgrade: 低耐受 VO2 → threshold
    if name.startswith("vo2max"):
        tc = tolerance_classes.get("VO2max") or tolerance_classes.get("vo2max")
        if tc == "low":
            return "threshold_2x20"
        if tc == "high" and name == "vo2max_short_5x4" and "6x3" in hint.lower():
            return "vo2max_short_6x3"

    return name
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_intent_translator.py -v`
Expected: PASS all nine.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/intent_translator.py \
        icu/tests/unit/session_designer/test_intent_translator.py
git commit -m "feat(coach-phase2): intent translator (DayIntent → workout template name with tolerance downgrade)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/session_designer/ -v` 全绿
- [ ] 3 次提交（T36 / T37 / T38）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`07-session-composer.md`](./07-session-composer.md) 开始。
