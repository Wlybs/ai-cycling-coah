# Phase 2 — Weekly assembler (Tasks T41–T42)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/session_designer/assembler.py`
- `icu/tests/unit/session_designer/test_assembler.py`

**Goal:** 把 Periodization 层的 `MicroCycle` 转成 7 个 `DesignedSession`，用 `safety_guards` 反复迭代修订，产出 `WeeklyPlan` + 每日 trace JSON；不调 Gemini（prose 在 T43 阶段单独一次）。

---

## Task 41: Assembler 主循环 — MicroCycle → WeeklyPlan

**Algorithm:**
1. 读 Phase 1 生理数据文件：
   - `coach_memory/physiology/cp_w_current.json`
   - `coach_memory/physiology/durability.json`
   - `coach_memory/physiology/response_profile.json`
2. 提取 `tolerance_classes` 字典（用于 intent_translator）
3. For each day in `micro_cycle.days`:
   - `template_name = translate_intent(tier, hint, tolerance_classes)`
   - `session = compose_session(intent, date, template_name, physiology, durability, response)`
   - Collect designed sessions
4. Assemble `WeeklyPlan`（v2 结构）:
   - `week_start/end` from micro_cycle
   - `focus_theme` = `f"{phase.value} week — primary: {intent.primary_adaptation}"`
   - `weekly_tss_target` = `micro_cycle.weekly_tss_target`
   - `coaching_summary` 留空（prose T43 填充）
   - `days` = 7 个 `DayPlanV2`（从 `DesignedSession` 映射字段）
5. 运行 `check_weekly_plan`，若有 violations 做**一次**自动修订（revise_plan），再跑一次 safety check；若仍有则记录到 trace 但不再修订（让 prose 层解释）
6. 返回 `(WeeklyPlan, list[DesignedSession], violations_remaining)`；designed sessions 与 plan 对齐的完整 structure 供 trace 写入

**Files:**
- Create: `icu/src/coach/session_designer/assembler.py`
- Create: `icu/tests/unit/session_designer/test_assembler.py`

- [ ] **Step 1: Write failing tests**

Write `icu/tests/unit/session_designer/test_assembler.py`:
```python
import json
from datetime import date
from pathlib import Path

from src.coach.periodization.types import (
    MicroCycle, DayIntent, IntensityTier, Phase, PhaseIntent,
)
from src.coach.session_designer.assembler import design_week
from src.coach.session_designer.types import WeeklyPlan


def _micro(phase: Phase = Phase.BUILD) -> MicroCycle:
    intent = PhaseIntent(
        phase=phase, primary_adaptation="threshold_capacity",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )
    template = [
        ("Mon", IntensityTier.REST, 0, "rest"),
        ("Tue", IntensityTier.HARD, 95, "VO2max 5x4' @ 110-115% CP"),
        ("Wed", IntensityTier.EASY, 40, "Z2 recovery 45min"),
        ("Thu", IntensityTier.MEDIUM, 75, "sweet-spot 3x12' @ 88-93% CP"),
        ("Fri", IntensityTier.REST, 0, "rest"),
        ("Sat", IntensityTier.HARD, 110, "threshold 2x20' @ 97-102% CP"),
        ("Sun", IntensityTier.MEDIUM, 180, "endurance 2.5h with 2x10' tempo"),
    ]
    days = [DayIntent(day_of_week=dow, tier=t, target_tss=tss,
                      session_hint=hint) for dow, t, tss, hint in template]
    return MicroCycle(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        phase=phase, intent=intent, days=days,
        weekly_tss_target=500,
    )


def _write_phys(tmp_path):
    p = tmp_path / "coach_memory" / "physiology"
    p.mkdir(parents=True)
    (p / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 280, "w_prime_joules": 22000,
        "fit_r_squared": 0.95, "athlete_ftp_set": 288,
    }))
    (p / "durability.json").write_text(json.dumps({
        "decay_rate_pct_per_1000kj": {"60s": 3.0, "300s": 2.0},
        "sample_size_rides": 12,
    }))
    (p / "response_profile.json").write_text(json.dumps({
        "types": {"Threshold": {"tolerance_class": "medium"},
                  "VO2max": {"tolerance_class": "medium"},
                  "Tempo": {"tolerance_class": "high"}},
        "knee_loading": {"flag": None, "standing_climb_minutes_90d": 0},
    }))
    return tmp_path


def test_design_week_returns_weekly_plan_with_7_days(tmp_path):
    _write_phys(tmp_path)
    plan, sessions, violations = design_week(
        micro_cycle=_micro(),
        memory_dir=tmp_path / "coach_memory",
    )
    assert isinstance(plan, WeeklyPlan)
    assert len(plan.days) == 7
    assert plan.weekly_tss_target == 500
    assert plan.days[0].training_type == "Rest"
    assert plan.days[1].training_type == "VO2max"
    assert len(sessions) == 7


def test_designed_sessions_trace_contains_cp_and_template(tmp_path):
    _write_phys(tmp_path)
    _plan, sessions, _ = design_week(
        micro_cycle=_micro(), memory_dir=tmp_path / "coach_memory",
    )
    tue = [s for s in sessions if s.day_of_week == "Tue"][0]
    assert tue.trace["cp_watts"] == 280
    assert tue.trace["template_name"] == "vo2max_short_5x4"


def test_hard_back_to_back_gets_revised_for_medium_tolerance(tmp_path):
    _write_phys(tmp_path)
    # 构造一个连续 HARD 的 micro：Tue HARD + Wed HARD
    micro = _micro()
    days = list(micro.days)
    days[2] = DayIntent(day_of_week="Wed", tier=IntensityTier.HARD,
                        target_tss=85, session_hint="threshold 2x15'")
    micro = micro.model_copy(update={"days": days})

    plan, _sessions, violations = design_week(
        micro_cycle=micro, memory_dir=tmp_path / "coach_memory",
    )
    # 一次自动修订后 Wed 应被降级为 MEDIUM 或 EASY（training_type 不再是 VO2max/Threshold）
    wed = plan.days[2]
    assert wed.training_type not in ("VO2max", "Threshold")


def test_clean_plan_has_empty_coaching_summary_pending_prose(tmp_path):
    _write_phys(tmp_path)
    plan, _sessions, _ = design_week(
        micro_cycle=_micro(), memory_dir=tmp_path / "coach_memory",
    )
    # prose 在 T43 阶段填充，assembler 产出时应为空字符串（占位）
    assert plan.coaching_summary == ""


def test_missing_physiology_still_produces_plan_using_ftp_fallback(tmp_path):
    mem = tmp_path / "coach_memory"
    mem.mkdir()
    plan, _s, _v = design_week(
        micro_cycle=_micro(), memory_dir=mem, fallback_ftp=285,
    )
    # 退化路径：未能读到 cp_w_current.json → 用 fallback_ftp 作为 CP
    assert plan.weekly_tss_target == 500
    assert len(plan.days) == 7
```

- [ ] **Step 2: Run — fail**

Expected: FAIL.

- [ ] **Step 3: Implement assembler**

Write `icu/src/coach/session_designer/assembler.py`:
```python
"""MicroCycle → WeeklyPlan。"""
from __future__ import annotations

import json
from datetime import date as DateT, timedelta
from pathlib import Path
from typing import Optional

from ..periodization.types import (
    DayIntent, IntensityTier, MicroCycle, Phase, SessionType,
)
from .composer import compose_session
from .intent_translator import translate_intent
from .safety_guards import SafetyViolation, check_weekly_plan
from .types import (
    DayPlanV2, DesignedSession, SessionIntent, WeeklyPlan,
)

DOW_DATES = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
             "Fri": 4, "Sat": 5, "Sun": 6}


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_physiology(
    memory_dir: Path, fallback_ftp: int = 280
) -> tuple[dict, dict, dict]:
    phys_dir = memory_dir / "physiology"
    cp_w = _load_json(phys_dir / "cp_w_current.json") or {}
    if not cp_w:
        cp_w = {"cp_watts": fallback_ftp, "w_prime_joules": 20000,
                "fit_r_squared": None, "athlete_ftp_set": fallback_ftp}
    dur = _load_json(phys_dir / "durability.json") or {}
    resp = _load_json(phys_dir / "response_profile.json") or {}
    return cp_w, dur, resp


def _tolerance_classes(resp: dict) -> dict[str, str]:
    types = (resp or {}).get("types") or {}
    out = {}
    for k, v in types.items():
        tc = (v or {}).get("tolerance_class")
        if tc:
            out[k] = tc
    return out


def _session_to_dayplan(s: DesignedSession) -> DayPlanV2:
    icu_type = "Rest" if s.session_type is SessionType.REST else "Ride"
    return DayPlanV2(
        date=s.date,
        day_of_week=s.day_of_week,
        training_type=s.session_type.value,
        icu_type=icu_type,
        name=s.name,
        description=s.description,
        duration_min=s.duration_min,
        target_tss=s.target_tss,
        power_range_w=s.power_range_w,
        hr_range_bpm=s.hr_range_bpm,
    )


def _revise_for_violations(
    days_intents: list[dict], violations: list[SafetyViolation]
) -> list[dict]:
    """基于 violations 做一次保守修订。规则同 safety_guards 的 suggested_action。"""
    out = [dict(d) for d in days_intents]
    for v in violations:
        if v.rule == "hard_back_to_back" and v.day_index is not None:
            out[v.day_index]["tier"] = "MEDIUM"
            # 替换 hint 为一个安全的 sweet-spot hint
            out[v.day_index]["session_hint"] = "sweet-spot 3x12'"
        elif v.rule == "knee_back_to_back_stand" and v.day_index is not None:
            out[v.day_index]["tier"] = "EASY"
            out[v.day_index]["session_hint"] = "recovery spin"
        elif v.rule == "w_prime_weekly_overdraw":
            # 把第 4 次起的 HARD 日降级为 MEDIUM（sweet-spot）
            hard_indices = [i for i, d in enumerate(out)
                            if str(d.get("tier", "")).upper() == "HARD"]
            for idx in hard_indices[3:]:
                out[idx]["tier"] = "MEDIUM"
                out[idx]["session_hint"] = "sweet-spot 3x12'"
        elif v.rule == "tss_budget_overflow":
            # 砍掉最后一个 EASY 日的 target
            for i in range(len(out) - 1, -1, -1):
                if out[i].get("tier") == "EASY" and out[i].get("target_tss", 0) > 0:
                    out[i]["target_tss"] = max(
                        0, int(out[i]["target_tss"] * 0.7))
                    break
        elif v.rule == "missing_rest_day":
            out[4]["tier"] = "REST"
            out[4]["session_hint"] = "rest"
            out[4]["target_tss"] = 0
    return out


def design_week(
    micro_cycle: MicroCycle,
    memory_dir: Path,
    fallback_ftp: int = 280,
) -> tuple[WeeklyPlan, list[DesignedSession], list[SafetyViolation]]:
    memory_dir = Path(memory_dir)
    phys, dur, resp = _load_physiology(memory_dir, fallback_ftp)
    tol = _tolerance_classes(resp)

    # 1) 转成 intent dict 供 safety + revision 使用
    day_dicts: list[dict] = []
    for di in micro_cycle.days:
        day_dicts.append({
            "day_of_week": di.day_of_week,
            "tier": di.tier.value,
            "target_tss": di.target_tss,
            "session_hint": di.session_hint,
        })

    # 2) 第一次 safety check（基于 intent）→ 修订一次
    first_violations = check_weekly_plan(
        day_dicts, weekly_tss_target=micro_cycle.weekly_tss_target,
        response_profile=resp, durability=dur,
        w_prime_joules=int(phys.get("w_prime_joules") or 20000),
    )
    revised = _revise_for_violations(day_dicts, first_violations)

    # 3) 再跑一次 safety — 记录 remaining
    remaining = check_weekly_plan(
        revised, weekly_tss_target=micro_cycle.weekly_tss_target,
        response_profile=resp, durability=dur,
        w_prime_joules=int(phys.get("w_prime_joules") or 20000),
    )

    # 4) 组装 DesignedSession
    sessions: list[DesignedSession] = []
    for idx, day in enumerate(revised):
        tier = IntensityTier(day["tier"])
        intent = SessionIntent(
            day_of_week=day["day_of_week"], tier=tier,
            target_tss=int(day["target_tss"]),
            session_hint=day["session_hint"],
        )
        template_name = translate_intent(
            tier=tier, hint=day["session_hint"],
            tolerance_classes=tol,
        )
        day_date = micro_cycle.week_start + timedelta(
            days=DOW_DATES[day["day_of_week"]])
        session = compose_session(
            intent=intent, date=day_date,
            template_name=template_name,
            physiology=phys, durability=dur,
            response_profile=resp,
        )
        sessions.append(session)

    # 5) 组装 WeeklyPlan
    plan = WeeklyPlan(
        week_start=micro_cycle.week_start.isoformat(),
        week_end=micro_cycle.week_end.isoformat(),
        focus_theme=(f"{micro_cycle.phase.value} week — "
                     f"primary: {micro_cycle.intent.primary_adaptation}"),
        weekly_tss_target=micro_cycle.weekly_tss_target,
        coaching_summary="",
        days=[_session_to_dayplan(s) for s in sessions],
    )

    return plan, sessions, remaining
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_assembler.py -v`
Expected: PASS all five.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/assembler.py \
        icu/tests/unit/session_designer/test_assembler.py
git commit -m "feat(coach-phase2): weekly assembler (MicroCycle→WeeklyPlan with one auto-revision pass)"
```

---

## Task 42: Trace writer for designed sessions

**Goal:** 一个独立的 `write_plan_trace()`，把 `list[DesignedSession]` + violations 写到 `reports/plan_YYYYMMDD.trace.json`，供 CLI 工具和历史对比使用。

**Files:**
- Modify: `icu/src/coach/session_designer/assembler.py`（append `write_plan_trace`）
- Modify: `icu/tests/unit/session_designer/test_assembler.py`（append）

- [ ] **Step 1: Write failing test**

Append to `test_assembler.py`:
```python
from datetime import date as _D
from src.coach.session_designer.assembler import write_plan_trace


def test_write_plan_trace_json_roundtrip(tmp_path):
    _write_phys(tmp_path)
    _plan, sessions, violations = design_week(
        micro_cycle=_micro(), memory_dir=tmp_path / "coach_memory",
    )
    out = tmp_path / "reports"
    path = write_plan_trace(
        out_dir=out, week_start=_D(2026, 4, 20),
        sessions=sessions, violations=violations,
        generated_at="2026-04-18T00:00:00Z",
    )
    doc = json.loads(Path(path).read_text())
    assert doc["generated_at"] == "2026-04-18T00:00:00Z"
    assert len(doc["days"]) == 7
    assert all("template_name" in d["trace"] for d in doc["days"])
    # violations 可以是空数组
    assert isinstance(doc["violations_remaining"], list)
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — function undefined.

- [ ] **Step 3: Implement**

Append to `icu/src/coach/session_designer/assembler.py`:
```python
def write_plan_trace(
    out_dir: Path,
    week_start: DateT,
    sessions: list[DesignedSession],
    violations: list[SafetyViolation],
    generated_at: str,
) -> str:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"plan_{week_start.strftime('%Y%m%d')}.trace.json"
    doc = {
        "generated_at": generated_at,
        "week_start": week_start.isoformat(),
        "days": [
            {
                "day_of_week": s.day_of_week,
                "date": s.date,
                "session_type": s.session_type.value,
                "template_name": s.trace.get("template_name") if s.trace else None,
                "trace": s.trace or {},
            }
            for s in sessions
        ],
        "violations_remaining": [v.model_dump() for v in violations],
    }
    path = out_dir / name
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    return str(path)
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_assembler.py -v`
Expected: PASS all six.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/assembler.py \
        icu/tests/unit/session_designer/test_assembler.py
git commit -m "feat(coach-phase2): plan trace writer (reports/plan_YYYYMMDD.trace.json)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/ -v` 全绿（periodization + session_designer 合计）
- [ ] 2 次提交（T41 / T42）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`09-prose-generator.md`](./09-prose-generator.md) 开始。
