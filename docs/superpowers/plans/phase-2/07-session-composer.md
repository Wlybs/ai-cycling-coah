# Phase 2 — Session composer (Tasks T39–T40)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/session_designer/composer.py`
- `icu/src/coach/session_designer/safety_guards.py`
- `icu/tests/unit/session_designer/test_composer.py`
- `icu/tests/unit/session_designer/test_safety_guards.py`

**Goal:** 把 `WorkoutTemplate` + `SessionIntent` + Phase 1 生理数据变成具体的 `DesignedSession`：瓦特范围、目标 TSS、描述文本骨架、trace 记录来源。安全护栏（膝盖、response tolerance、W' 预算）在独立模块里，让 composer 保持纯粹。

---

## Task 39: Composer — template + CP/W'/durability → DesignedSession

**Files:**
- Create: `icu/src/coach/session_designer/composer.py`
- Create: `icu/tests/unit/session_designer/test_composer.py`

### Core algorithm

1. **Resolve targets** — 对模板每个 step，把 `pct_of_cp_low/high` 乘以 `cp_watts` 得到绝对瓦特
2. **Duration scaling** — 如果 `target_tss` 在模板 `total_duration_s_range` 内能达成（按 estimated TSS 计算），直接用模板默认；否则：
   - 长骑类（`endurance_*`）：按目标 TSS 线性缩放主集时长
   - 间歇类：保持结构不变，前后 Z2 段微调 ±15%
3. **TSS estimation** — 对每步用 `tss_step = (duration_s / 3600) * (IF^2) * 100`，其中 IF = pct_of_cp_mid（取 low/high 均值）
4. **Aggregate** — `total_duration_min = ceil(total_s/60)`；`power_range_w = "{min}-{max}W"` 取主集 step 最低 low 与最高 high
5. **Description** — 一行文本：`"WU 15min, 5x(4min @ 110-115% CP, r3min Z1), CD 10min"`（composer 生成骨架；Gemini prose 阶段 T43 再补充叙述）
6. **Trace** — 记录 `{template_name, cp_watts, w_prime_joules, durability_applied, tss_estimated, tss_target, duration_stretched_pct}`

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/session_designer/test_composer.py`:
```python
from datetime import date

from src.coach.session_designer.composer import compose_session
from src.coach.session_designer.types import SessionIntent
from src.coach.periodization.types import IntensityTier, SessionType


def _physiology(cp=280, w_prime=22000):
    return {"cp_watts": cp, "w_prime_joules": w_prime, "fit_r_squared": 0.95,
            "athlete_ftp_set": 288, "cp_vs_ftp_delta_w": -8}


def test_compose_threshold_session_produces_watts():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=280),
        durability={}, response_profile={},
    )
    assert session.session_type is SessionType.THRESHOLD
    # 2x20 main 段的 watts 应该 ≈ 97-102% × 280
    main_steps = [s for s in session.structure.steps if "TH" in s.label]
    for step in main_steps:
        assert step.target_w_low is not None
        assert 270 <= step.target_w_low <= 275
        assert 285 <= step.target_w_high <= 290
    assert "W" in (session.power_range_w or "")


def test_compose_long_z2_stretches_duration_to_match_tss():
    intent = SessionIntent(
        day_of_week="Sun", tier=IntensityTier.EASY,
        target_tss=160, session_hint="long Z2 3h+",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 26),
        template_name="endurance_long_z2",
        physiology=_physiology(cp=280),
        durability={"decay_rate_pct_per_1000kj": {"60s": 3.0, "300s": 2.0}},
        response_profile={},
    )
    # 长骑 main 段应该被拉长到 ~3.5-4h 以打到 TSS 160
    assert session.duration_min >= 180
    assert session.target_tss == 160
    # trace 必须记录 stretch
    assert session.trace is not None
    assert "duration_stretched_pct" in session.trace


def test_compose_rest_day_returns_empty_structure():
    intent = SessionIntent(
        day_of_week="Mon", tier=IntensityTier.REST,
        target_tss=0, session_hint="rest",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 20),
        template_name="rest_day",
        physiology=_physiology(), durability={}, response_profile={},
    )
    assert session.session_type is SessionType.REST
    assert session.duration_min == 0
    assert len(session.structure.steps) == 0


def test_compose_uses_cp_not_ftp_when_different():
    # CP 低于 FTP 的情况 — 必须用 CP
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=90, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=265),  # CP 远低于 FTP=288
        durability={}, response_profile={},
    )
    main = [s for s in session.structure.steps if "TH" in s.label][0]
    # 97% × 265 = 257
    assert main.target_w_low < 260


def test_compose_tss_within_15pct_of_target_for_intervals():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=280),
        durability={}, response_profile={},
    )
    diff = abs(session.target_tss - 95)
    assert diff <= 95 * 0.15


def test_description_contains_schema():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(), durability={}, response_profile={},
    )
    desc = session.description.lower()
    # 至少包含 WU/CD 的时间指示和主集
    assert "wu" in desc or "warmup" in desc or "热身" in desc
    assert "cd" in desc or "cooldown" in desc or "整理" in desc


def test_trace_records_cp_and_template_name():
    intent = SessionIntent(
        day_of_week="Tue", tier=IntensityTier.HARD,
        target_tss=95, session_hint="threshold 2x20'",
    )
    session = compose_session(
        intent=intent, date=date(2026, 4, 21),
        template_name="threshold_2x20",
        physiology=_physiology(cp=280, w_prime=22000),
        durability={"decay_rate_pct_per_1000kj": {"60s": 3.0}},
        response_profile={"types": {"Threshold": {"tolerance_class": "medium"}}},
    )
    trace = session.trace
    assert trace["template_name"] == "threshold_2x20"
    assert trace["cp_watts"] == 280
    assert trace["w_prime_joules"] == 22000
    assert "tss_estimated" in trace
```

- [ ] **Step 2: Run — fail**

Expected: FAIL.

- [ ] **Step 3: Implement composer**

Write `icu/src/coach/session_designer/composer.py`:
```python
"""把 WorkoutTemplate + 生理数据变成一个 DesignedSession。"""
from __future__ import annotations

import math
from datetime import date as DateT
from typing import Optional

from ..periodization.types import SessionType
from .types import (
    DesignedSession, SessionIntent, SessionStructure, WorkoutStep,
)
from .workout_library import (
    WorkoutTemplate, WorkoutTemplateStep, get_template,
)

TSS_STEP_COEF = 100.0


def _mid(low: Optional[float], high: Optional[float]) -> Optional[float]:
    if low is None or high is None:
        return None
    return (low + high) / 2.0


def _step_watts(
    step: WorkoutTemplateStep, cp: int
) -> tuple[Optional[int], Optional[int]]:
    if step.pct_of_cp_low is None or step.pct_of_cp_high is None:
        return (None, None)
    return (int(round(step.pct_of_cp_low * cp)),
            int(round(step.pct_of_cp_high * cp)))


def _step_tss(step: WorkoutTemplateStep) -> float:
    mid = _mid(step.pct_of_cp_low, step.pct_of_cp_high)
    if mid is None:
        return 0.0
    return (step.duration_s / 3600.0) * (mid ** 2) * TSS_STEP_COEF


def _estimate_template_tss(template: WorkoutTemplate) -> float:
    return sum(_step_tss(s) for s in template.steps)


def _convert_step(tpl_step: WorkoutTemplateStep, cp: int) -> WorkoutStep:
    low, high = _step_watts(tpl_step, cp)
    return WorkoutStep(
        label=tpl_step.label,
        duration_s=tpl_step.duration_s,
        target_w_low=low, target_w_high=high,
        zone=tpl_step.zone,
    )


def _scale_long_ride_to_tss(
    template: WorkoutTemplate, cp: int, target_tss: int
) -> tuple[list[WorkoutStep], float]:
    """对 endurance_long_* 模板按 target_tss 拉伸/压缩主集时长。"""
    converted = [_convert_step(s, cp) for s in template.steps]
    main_indices = [i for i, s in enumerate(template.steps)
                    if s.label not in ("WU", "CD")
                    and s.pct_of_cp_low is not None
                    and s.pct_of_cp_low < 0.80]  # Z2 段
    if not main_indices:
        return converted, 0.0
    # 计算当前 estimated TSS，以及 main Z2 段对 TSS 的贡献/秒
    estimated = sum(_step_tss(template.steps[i]) for i in range(len(template.steps)))
    main_tss = sum(_step_tss(template.steps[i]) for i in main_indices)
    if main_tss <= 0 or estimated <= 0:
        return converted, 0.0
    needed = target_tss - (estimated - main_tss)
    if needed <= 0:
        # target 太低 → 压缩到 min range
        stretch = template.total_duration_s_range[0] / sum(
            s.duration_s for s in template.steps)
    else:
        # 主段总 TSS per second
        main_seconds = sum(template.steps[i].duration_s for i in main_indices)
        main_tss_per_s = main_tss / main_seconds
        new_main_seconds = max(600, needed / main_tss_per_s)
        stretch = new_main_seconds / main_seconds
        # 把 stretch 限定在模板 duration_range 内
        total_s = (stretch * main_seconds
                   + sum(template.steps[i].duration_s
                         for i in range(len(template.steps))
                         if i not in main_indices))
        lo, hi = template.total_duration_s_range
        if total_s > hi:
            stretch = (hi - sum(template.steps[i].duration_s
                                for i in range(len(template.steps))
                                if i not in main_indices)) / main_seconds
        if total_s < lo:
            stretch = (lo - sum(template.steps[i].duration_s
                                for i in range(len(template.steps))
                                if i not in main_indices)) / main_seconds
    for i in main_indices:
        orig = converted[i]
        converted[i] = WorkoutStep(
            label=orig.label,
            duration_s=int(round(orig.duration_s * stretch)),
            target_w_low=orig.target_w_low,
            target_w_high=orig.target_w_high,
            zone=orig.zone,
        )
    return converted, stretch


def _power_range_summary(steps: list[WorkoutStep]) -> Optional[str]:
    main = [s for s in steps if s.label not in ("WU", "CD", "rest")
            and s.target_w_low is not None and s.target_w_high is not None]
    if not main:
        return None
    lo = min(s.target_w_low for s in main)
    hi = max(s.target_w_high for s in main)
    return f"{lo}-{hi}W"


def _build_description(
    template: WorkoutTemplate, steps: list[WorkoutStep]
) -> str:
    """一行文本骨架：'WU 15', main, CD 10'。"""
    parts: list[str] = []
    for s in steps:
        minutes = max(1, round(s.duration_s / 60))
        if s.target_w_low and s.target_w_high:
            parts.append(f"{s.label} {minutes}min @ {s.target_w_low}-{s.target_w_high}W")
        else:
            parts.append(f"{s.label} {minutes}min")
    return "; ".join(parts)


def compose_session(
    intent: SessionIntent,
    date: DateT,
    template_name: str,
    physiology: dict,
    durability: dict,
    response_profile: dict,
) -> DesignedSession:
    template = get_template(template_name)
    cp = int(physiology.get("cp_watts") or physiology.get("athlete_ftp_set") or 280)
    w_prime = int(physiology.get("w_prime_joules") or 20000)

    # 决定是否拉伸长骑
    stretch = 1.0
    if template.name.startswith("endurance_long") and intent.target_tss > 0:
        steps, stretch = _scale_long_ride_to_tss(template, cp, intent.target_tss)
    else:
        steps = [_convert_step(s, cp) for s in template.steps]

    structure = SessionStructure(steps=steps)
    total_min = max(0, int(math.ceil(structure.total_duration_s / 60)))

    # TSS 估算（使用缩放后的 steps）
    tss_est = 0.0
    for s in steps:
        mid = _mid(
            (s.target_w_low / cp) if s.target_w_low else None,
            (s.target_w_high / cp) if s.target_w_high else None,
        )
        if mid is None:
            continue
        tss_est += (s.duration_s / 3600.0) * (mid ** 2) * TSS_STEP_COEF

    # 最终使用哪个 TSS 作为 day target：
    # - 间歇类：若估算与 target 差 <15%，用 target；否则用估算
    # - 长骑：stretch 已把估算校准到 target，优先 target
    final_tss = intent.target_tss
    if template.name.startswith("endurance_long"):
        final_tss = intent.target_tss
    else:
        diff_pct = abs(tss_est - intent.target_tss) / max(intent.target_tss, 1)
        final_tss = intent.target_tss if diff_pct <= 0.15 else int(round(tss_est))

    trace = {
        "template_name": template.name,
        "cp_watts": cp,
        "w_prime_joules": w_prime,
        "tss_estimated": round(tss_est, 1),
        "tss_target": intent.target_tss,
        "duration_stretched_pct": round((stretch - 1.0) * 100, 1),
        "durability_applied": bool(durability.get("decay_rate_pct_per_1000kj")),
        "tolerance_class": (response_profile.get("types") or {})
            .get(template.session_type.value, {}).get("tolerance_class"),
    }

    return DesignedSession(
        day_of_week=intent.day_of_week,
        date=date.isoformat(),
        session_type=template.session_type,
        name=_session_display_name(template, cp),
        description=_build_description(template, steps),
        duration_min=total_min,
        target_tss=max(0, min(400, int(final_tss))),
        structure=structure,
        power_range_w=_power_range_summary(steps),
        trace=trace,
    )


def _session_display_name(template: WorkoutTemplate, cp: int) -> str:
    """给出用户可读的 session 名字。"""
    mapping = {
        "vo2max_short_5x4": f"VO2max 5×4' @ {int(cp*1.10)}-{int(cp*1.15)}W",
        "vo2max_short_6x3": f"VO2max 6×3' @ {int(cp*1.15)}-{int(cp*1.20)}W",
        "threshold_2x20": f"Threshold 2×20' @ {int(cp*0.97)}-{int(cp*1.02)}W",
        "sweet_spot_3x15": f"Sweet-spot 3×15' @ {int(cp*0.88)}-{int(cp*0.93)}W",
        "tempo_continuous_60": f"Tempo 60' @ {int(cp*0.80)}-{int(cp*0.85)}W",
        "endurance_long_z2": "Long Z2 endurance",
        "endurance_long_with_tempo": "Long endurance + tempo",
        "recovery_spin": "Recovery spin",
        "openers_short": "Openers 4×30''",
        "race_sim_course": "Race simulation",
        "rest_day": "Rest",
    }
    return mapping.get(template.name, template.name)
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_composer.py -v`
Expected: PASS all seven.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/composer.py \
        icu/tests/unit/session_designer/test_composer.py
git commit -m "feat(coach-phase2): session composer (CP/W'-parameterized template → DesignedSession)"
```

---

## Task 40: Safety guardrails (knee + W' budget + response tolerance)

**Goal:** 独立模块 `safety_guards.py`，接收 `WeeklyPlan` 草稿 + `response_profile` + `durability`，返回违规清单 + 建议的修订。由 assembler 在 T42 调用。

### Rules

| Rule | Trigger | Action |
|---|---|---|
| knee_back_to_back_stand | response.knee_loading.flag in {watch, caution} 且连续 2 天有模板含 `standing climb / openers`（关键字匹配） | 把第二天改为 rest_day 或 recovery_spin |
| hard_back_to_back | 连续 2 天 HARD 且 response.types.<type>.tolerance_class != "high" | 把第二天降级 (HARD → MEDIUM) |
| w_prime_weekly_overdraw | 一周 HARD 日数 ≥ 4 | 第 4 次起的 HARD 日降级为 MEDIUM（用户决策 2026-04-18：正常 BUILD 周 2–3 次 HARD 是常态，第 4 次起警告） |
| tss_budget_overflow | `sum(day.target_tss)` 超过 `weekly_tss_target * 1.15` | 把最后一天 EASY 的 target_tss 砍到 0 |
| missing_rest_day | 7 天里没有任何 REST | 强制把周五或周一改 REST |

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/session_designer/test_safety_guards.py`:
```python
from src.coach.session_designer.safety_guards import (
    check_weekly_plan, SafetyViolation,
)


def _day(i, tss, hint, tier="HARD"):
    return {
        "day_of_week": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][i],
        "tier": tier, "target_tss": tss, "session_hint": hint,
    }


def test_back_to_back_hard_flagged():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 90, "VO2max 5x4", "HARD"),
        _day(3, 40, "recovery", "EASY"),
        _day(4, 0, "rest", "REST"),
        _day(5, 110, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=465, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "hard_back_to_back" for v in violations)


def test_knee_back_to_back_standing_violation():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 90, "standing climb intervals 5x5", "HARD"),
        _day(2, 95, "standing climb attacks", "HARD"),
        _day(3, 40, "recovery", "EASY"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=470,
        response_profile={"knee_loading": {"flag": "caution"}},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "knee_back_to_back_stand" for v in violations)


def test_tss_overflow_flagged():
    days = [_day(i, 120, "x", "HARD") for i in range(7)]
    violations = check_weekly_plan(
        days, weekly_tss_target=500, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "tss_budget_overflow" for v in violations)


def test_missing_rest_day_flagged():
    days = [_day(i, 60, "tempo", "EASY") for i in range(7)]
    violations = check_weekly_plan(
        days, weekly_tss_target=420, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert any(v.rule == "missing_rest_day" for v in violations)


def test_high_tolerance_allows_back_to_back_hard():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 90, "VO2max 5x4", "HARD"),
        _day(3, 40, "recovery", "EASY"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=465,
        response_profile={
            "types": {"Threshold": {"tolerance_class": "high"},
                      "VO2max": {"tolerance_class": "high"}}
        }, durability={}, w_prime_joules=22000,
    )
    assert not any(v.rule == "hard_back_to_back" for v in violations)


def test_no_violations_on_clean_plan():
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 40, "recovery", "EASY"),
        _day(3, 75, "sweet-spot 3x15", "MEDIUM"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=440, response_profile={},
        durability={}, w_prime_joules=22000,
    )
    assert len(violations) == 0


def test_three_hard_days_does_not_trigger_w_prime_rule():
    """标准 BUILD 周 2-3 次 HARD 是常态，不应报警。"""
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 40, "recovery", "EASY"),
        _day(3, 90, "VO2max 5x4", "HARD"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=455,
        response_profile={"types": {
            "Threshold": {"tolerance_class": "high"},
            "VO2max": {"tolerance_class": "high"}}},
        durability={}, w_prime_joules=22000,
    )
    assert not any(v.rule == "w_prime_weekly_overdraw" for v in violations)


def test_four_hard_days_triggers_w_prime_rule():
    """≥ 4 次 HARD 触发累积疲劳警告（用户决策 2026-04-18）。"""
    days = [
        _day(0, 0, "rest", "REST"),
        _day(1, 95, "threshold 2x20", "HARD"),
        _day(2, 90, "VO2max 5x4", "HARD"),
        _day(3, 85, "threshold 2x15", "HARD"),
        _day(4, 0, "rest", "REST"),
        _day(5, 100, "threshold 2x20", "HARD"),
        _day(6, 130, "long Z2", "EASY"),
    ]
    violations = check_weekly_plan(
        days, weekly_tss_target=500,
        response_profile={"types": {
            "Threshold": {"tolerance_class": "high"},
            "VO2max": {"tolerance_class": "high"}}},
        durability={}, w_prime_joules=22000,
    )
    w_p = [v for v in violations if v.rule == "w_prime_weekly_overdraw"]
    assert len(w_p) == 1
    # day_index 指向第 4 次 HARD（周六 index=5）
    assert w_p[0].day_index == 5
```

- [ ] **Step 2: Run — fail**

Expected: FAIL.

- [ ] **Step 3: Implement safety_guards**

Write `icu/src/coach/session_designer/safety_guards.py`:
```python
"""周计划安全护栏。给 assembler 在 T42 用。"""
from __future__ import annotations

from pydantic import BaseModel

STAND_KEYWORDS = ("stand", "standing climb", "摇车", "attack")
HARD_DAYS_WEEKLY_LIMIT = 4  # 一周 HARD 日数阈值（用户决策 2026-04-18）


class SafetyViolation(BaseModel):
    rule: str
    day_index: int | None = None
    message: str
    suggested_action: str


def _is_hard(day: dict) -> bool:
    return str(day.get("tier", "")).upper() == "HARD"


def _has_stand_keyword(hint: str) -> bool:
    h = hint.lower()
    return any(k in h for k in STAND_KEYWORDS)


def _tolerance_allows_hard_back_to_back(
    response_profile: dict, day1: dict, day2: dict
) -> bool:
    types = (response_profile or {}).get("types") or {}
    for day in (day1, day2):
        hint = day.get("session_hint", "").lower()
        key = None
        if "vo2" in hint: key = "VO2max"
        elif "threshold" in hint: key = "Threshold"
        elif "sweet" in hint: key = "Tempo"
        if key:
            tc = (types.get(key) or {}).get("tolerance_class")
            if tc != "high":
                return False
        else:
            return False
    return True


def check_weekly_plan(
    days: list[dict],
    weekly_tss_target: int,
    response_profile: dict,
    durability: dict,
    w_prime_joules: int,
) -> list[SafetyViolation]:
    out: list[SafetyViolation] = []

    # Rule: missing rest day
    if not any(str(d.get("tier", "")).upper() == "REST" for d in days):
        out.append(SafetyViolation(
            rule="missing_rest_day",
            message="本周无 REST 日",
            suggested_action="把周五或周一改 REST",
        ))

    # Rule: hard back-to-back
    for i in range(len(days) - 1):
        if _is_hard(days[i]) and _is_hard(days[i+1]):
            if not _tolerance_allows_hard_back_to_back(
                response_profile, days[i], days[i+1]
            ):
                out.append(SafetyViolation(
                    rule="hard_back_to_back",
                    day_index=i+1,
                    message=f"连续 HARD：{days[i]['day_of_week']} & "
                            f"{days[i+1]['day_of_week']}",
                    suggested_action="把第二天降级为 MEDIUM 或 EASY",
                ))

    # Rule: knee back-to-back standing
    knee_flag = (response_profile or {}).get("knee_loading", {}).get("flag")
    if knee_flag in ("watch", "caution"):
        for i in range(len(days) - 1):
            if (_has_stand_keyword(days[i].get("session_hint", ""))
                    and _has_stand_keyword(days[i+1].get("session_hint", ""))):
                out.append(SafetyViolation(
                    rule="knee_back_to_back_stand",
                    day_index=i+1,
                    message=f"连续 2 天出现站骑/摇车动作，knee_flag={knee_flag}",
                    suggested_action="把第二天改为 rest 或 recovery_spin",
                ))

    # Rule: TSS budget overflow
    total_tss = sum(int(d.get("target_tss", 0)) for d in days)
    if total_tss > weekly_tss_target * 1.15:
        out.append(SafetyViolation(
            rule="tss_budget_overflow",
            message=f"周 TSS {total_tss} > target {weekly_tss_target} * 1.15",
            suggested_action="把最后一个 EASY 日的 target_tss 下调",
        ))

    # Rule: W' weekly overdraw — 一周 HARD 日数 ≥ 4 即触发（用户决策 2026-04-18）
    # 阈值依据：标准 BUILD 周 2–3 次 HARD 是常态；≥4 次累积疲劳风险显著，需降级。
    hard_count = sum(1 for d in days if _is_hard(d))
    if hard_count >= HARD_DAYS_WEEKLY_LIMIT:
        # 定位第 4 次 HARD 的索引，告诉 assembler 从哪里开始降级
        hard_indices = [i for i, d in enumerate(days) if _is_hard(d)]
        fourth_hard = hard_indices[HARD_DAYS_WEEKLY_LIMIT - 1]
        out.append(SafetyViolation(
            rule="w_prime_weekly_overdraw",
            day_index=fourth_hard,
            message=f"本周 HARD 日 {hard_count} 次 "
                    f"(阈值 {HARD_DAYS_WEEKLY_LIMIT})，累积疲劳风险",
            suggested_action=f"把第 {HARD_DAYS_WEEKLY_LIMIT} 次起的 HARD 日降级为 MEDIUM",
        ))

    return out
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_safety_guards.py -v`
Expected: PASS all six.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/safety_guards.py \
        icu/tests/unit/session_designer/test_safety_guards.py
git commit -m "feat(coach-phase2): safety guards (knee, hard b2b, TSS overflow, rest day, W' overdraw)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/session_designer/ -v` 全绿
- [ ] 2 次提交（T39 / T40）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`08-weekly-assembler.md`](./08-weekly-assembler.md) 开始。
