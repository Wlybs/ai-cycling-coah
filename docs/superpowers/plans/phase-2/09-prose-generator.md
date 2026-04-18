# Phase 2 — Prose generator (Tasks T43–T44)

> Part of the Phase 2 implementation plan. See [00-index.md](./00-index.md).

**Files covered:**
- `icu/src/coach/session_designer/prose_generator.py`
- `icu/prompts/session_designer/prose_prompt.md`（新建目录）
- `icu/tests/unit/session_designer/test_prose_generator.py`

**Goal:** 一次 Gemini 调用，**只**负责把结构化 `WeeklyPlan` + 生理上下文 + 阶段 rationale + 未解决 violations 渲染成教练口吻的中文叙述（`coaching_summary` + 每日 `description` 的自然语言增强）。Gemini 不再做任何数学、强度决策、区间计算 — 这些已由 composer/assembler 完成。

---

## Task 43: Prose prompt + Gemini call

**Key design:**
- 单次调用、`response_schema` 约束 JSON 输出，确保字段回填不会损坏结构
- Prompt 传入完整 `WeeklyPlan`（可直接序列化）+ PhaseIntent.rationale + violations_remaining 文本
- 强制指令："you must NOT change any numeric field (duration_min, target_tss, power_range_w, etc.)"
- 超时 + 失败回退：API 超时 / JSON 解析失败 → 返回带默认叙述的 plan（`coaching_summary="生成叙述失败，参考每日 description 与 trace."`），不阻塞 push_plan

**Files:**
- Create: `icu/prompts/session_designer/prose_prompt.md`
- Create: `icu/src/coach/session_designer/prose_generator.py`
- Create: `icu/tests/unit/session_designer/test_prose_generator.py`

### Prompt structure（ground truth）

```
# 角色
你是一位顶尖职业自行车教练，正在把结构化周训练方案翻译成中文叙述性解读。

# 约束（绝对不能违反）
- 禁止修改 plan.days[*].duration_min / target_tss / power_range_w / hr_range_bpm / name / training_type / icu_type。
- 你只填充：coaching_summary（整周叙述），以及每一天的 description（替换为更有深度的教练语言，但字段保留）。
- 每日 description 必须覆盖：主集强度目的、本日 fueling 要点（若是长骑或 hard 日）、与本周 PhaseIntent 的关系。
- 100% 用中文，但核心名词保留英文（CP、W'、VO2max、Z4 等）。
- 如有 violations_remaining，必须在 coaching_summary 里用一句话解释为什么没有完美规避。

# 输入
PhaseIntent rationale: <intent.rationale>
Phase: <micro.phase>
WeeklyPlan (JSON): <dumped weekly plan>
Violations remaining (JSON): <dumped list>
Physiology snapshot (短摘要): CP=<cp>W / W'=<wp>J / durability decay 60s=<x>%/1000kJ / knee_flag=<flag>

# 输出 JSON schema
{
  "coaching_summary": str,        # 150-400 字
  "days": [
    {"date": str, "description": str},    # 每日 60-180 字
    ... (7 个)
  ]
}
```

- [ ] **Step 1: Write prompt file**

Write `icu/prompts/session_designer/prose_prompt.md` with the above content (Chinese).

- [ ] **Step 2: Write failing tests (with mocked Gemini client)**

Write `icu/tests/unit/session_designer/test_prose_generator.py`:
```python
import json
from types import SimpleNamespace

from src.coach.session_designer.prose_generator import (
    enrich_with_prose, render_prose_prompt,
)
from src.coach.session_designer.types import DayPlanV2, WeeklyPlan


def _make_plan():
    days = [
        DayPlanV2(date="2026-04-20", day_of_week="Mon",
                  training_type="Rest", icu_type="Rest",
                  name="Rest", description="rest",
                  duration_min=0, target_tss=0),
        DayPlanV2(date="2026-04-21", day_of_week="Tue",
                  training_type="VO2max", icu_type="Ride",
                  name="VO2max 5x4", description="skeleton",
                  duration_min=75, target_tss=95,
                  power_range_w="308-322W"),
    ] + [
        DayPlanV2(date=f"2026-04-{d}", day_of_week=dow,
                  training_type="Aerobic", icu_type="Ride",
                  name=f"Z2 {d}", description="skeleton",
                  duration_min=60, target_tss=40)
        for d, dow in [(22,"Wed"),(23,"Thu"),(24,"Fri"),(25,"Sat"),(26,"Sun")]
    ]
    return WeeklyPlan(
        week_start="2026-04-20", week_end="2026-04-26",
        focus_theme="BUILD week — threshold_capacity",
        weekly_tss_target=500, coaching_summary="",
        days=days,
    )


def test_render_prose_prompt_mentions_all_required_context():
    plan = _make_plan()
    prompt = render_prose_prompt(
        plan=plan,
        phase_rationale="Allen-Coggan Build week",
        phase_value="BUILD",
        physiology_summary={"cp": 280, "w_prime": 22000,
                            "durability_60s_pct": 3.0, "knee_flag": None},
        violations=[],
    )
    assert "BUILD" in prompt
    assert "CP=280" in prompt or "CP: 280" in prompt
    assert "threshold_capacity" in prompt
    assert "禁止修改" in prompt


def test_enrich_with_prose_fills_summary_and_descriptions(monkeypatch):
    plan = _make_plan()

    fake_payload = {
        "coaching_summary": "本周 BUILD week ...（150+ chars of coach prose）" * 3,
        "days": [
            {"date": d.date, "description": f"enriched {d.day_of_week}"}
            for d in plan.days
        ],
    }

    class _FakeResp:
        text = json.dumps(fake_payload, ensure_ascii=False)
        usage_metadata = SimpleNamespace(prompt_token_count=0,
                                         candidates_token_count=0)

    class _FakeModels:
        def generate_content(self, **kwargs):
            return _FakeResp()

    class _FakeClient:
        models = _FakeModels()

    result = enrich_with_prose(
        plan=plan,
        phase_rationale="r", phase_value="BUILD",
        physiology_summary={"cp": 280, "w_prime": 22000,
                            "durability_60s_pct": 3.0, "knee_flag": None},
        violations=[],
        client=_FakeClient(),
    )
    assert result.coaching_summary.startswith("本周 BUILD week")
    assert result.days[1].description == "enriched Tue"


def test_enrich_falls_back_when_api_fails(monkeypatch):
    plan = _make_plan()

    class _FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("network down")

    class _FakeClient:
        models = _FakeModels()

    result = enrich_with_prose(
        plan=plan,
        phase_rationale="r", phase_value="BUILD",
        physiology_summary={"cp": 280, "w_prime": 22000,
                            "durability_60s_pct": 3.0, "knee_flag": None},
        violations=[],
        client=_FakeClient(),
    )
    # 回退：skeleton 不变、coaching_summary 是 fallback 文案
    assert "生成叙述失败" in result.coaching_summary
    assert result.days[1].description == "skeleton"


def test_enrich_does_not_mutate_numeric_fields(monkeypatch):
    plan = _make_plan()

    # 恶意回传：改 duration_min 和 power_range_w
    mal_payload = {
        "coaching_summary": "ok",
        "days": [
            {"date": plan.days[1].date,
             "description": "custom",
             "duration_min": 9999,
             "power_range_w": "999-9999W"},
        ] + [
            {"date": d.date, "description": "x"} for d in plan.days[2:]
        ] + [{"date": plan.days[0].date, "description": "x"}],
    }

    class _FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text=json.dumps(mal_payload, ensure_ascii=False),
                usage_metadata=SimpleNamespace(
                    prompt_token_count=0, candidates_token_count=0),
            )

    class _FakeClient:
        models = _FakeModels()

    result = enrich_with_prose(
        plan=plan, phase_rationale="r", phase_value="BUILD",
        physiology_summary={"cp": 280, "w_prime": 22000,
                            "durability_60s_pct": 3.0, "knee_flag": None},
        violations=[],
        client=_FakeClient(),
    )
    tue = [d for d in result.days if d.day_of_week == "Tue"][0]
    # 被保留原值
    assert tue.duration_min == 75
    assert tue.power_range_w == "308-322W"
    # description 允许被替换
    assert tue.description == "custom"
```

- [ ] **Step 3: Run — fail**

Expected: FAIL — module undefined.

- [ ] **Step 4: Implement prose_generator**

Write `icu/src/coach/session_designer/prose_generator.py`:
```python
"""唯一一次 Gemini 调用：把结构化 WeeklyPlan 包装成中文叙述。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from ..common.logging import get_logger
from .types import DayPlanV2, WeeklyPlan

LOG = get_logger("session_designer_prose")

PROMPT_FILE = Path(__file__).resolve().parent.parent.parent.parent / \
    "prompts" / "session_designer" / "prose_prompt.md"

FALLBACK_COACH = "生成叙述失败，参考每日 description 与 trace.json 自行查看结构。"


class _ProseDay(BaseModel):
    date: str
    description: str


class _ProseEnvelope(BaseModel):
    coaching_summary: str
    days: list[_ProseDay]


def _load_prompt_template() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    # 默认 fallback prompt — 保持与 prose_prompt.md 对齐
    return (
        "# 角色\n你是顶尖职业自行车教练。\n\n"
        "# 约束\n禁止修改 duration_min / target_tss / power_range_w / "
        "hr_range_bpm / name / training_type / icu_type。\n"
        "你只填充 coaching_summary 和每日 description。\n\n"
        "# 输入\n<PAYLOAD>\n\n# 输出 JSON\n"
        "{\"coaching_summary\": str, \"days\": [{\"date\": str, "
        "\"description\": str}, ...]}"
    )


def render_prose_prompt(
    plan: WeeklyPlan,
    phase_rationale: str,
    phase_value: str,
    physiology_summary: dict,
    violations: list,
) -> str:
    base = _load_prompt_template()
    payload = {
        "phase": phase_value,
        "phase_rationale": phase_rationale,
        "plan": plan.model_dump(),
        "violations_remaining": violations,
        "physiology": {
            "CP": physiology_summary.get("cp"),
            "w_prime": physiology_summary.get("w_prime"),
            "durability_60s_pct": physiology_summary.get("durability_60s_pct"),
            "knee_flag": physiology_summary.get("knee_flag"),
        },
    }
    physio_line = (
        f"CP={physiology_summary.get('cp')}W / "
        f"W'={physiology_summary.get('w_prime')}J / "
        f"durability decay 60s={physiology_summary.get('durability_60s_pct')}%/1000kJ / "
        f"knee_flag={physiology_summary.get('knee_flag')}"
    )
    return (
        base
        + "\n\n# 实际输入\n"
        + f"Phase: {phase_value}\n"
        + f"PhaseIntent rationale: {phase_rationale}\n"
        + f"WeeklyPlan (JSON): {json.dumps(plan.model_dump(), ensure_ascii=False)}\n"
        + f"Violations remaining (JSON): {json.dumps(violations, ensure_ascii=False)}\n"
        + f"Physiology: {physio_line}\n"
    )


def _parse_envelope(text: str) -> Optional[_ProseEnvelope]:
    try:
        doc = json.loads(text)
        return _ProseEnvelope.model_validate(doc)
    except Exception as e:
        LOG.event(action="parse_prose", status="error", error=str(e))
        return None


def _apply_envelope(plan: WeeklyPlan,
                    env: _ProseEnvelope) -> WeeklyPlan:
    by_date = {d.date: d for d in env.days}
    new_days: list[DayPlanV2] = []
    for day in plan.days:
        prose = by_date.get(day.date)
        if prose:
            new_days.append(day.model_copy(
                update={"description": prose.description}))
        else:
            new_days.append(day)
    return plan.model_copy(update={
        "coaching_summary": env.coaching_summary,
        "days": new_days,
    })


def enrich_with_prose(
    plan: WeeklyPlan,
    phase_rationale: str,
    phase_value: str,
    physiology_summary: dict,
    violations: list,
    client: Any,
    model: str = "gemini-2.5-flash",
) -> WeeklyPlan:
    """调用 Gemini 生成 coaching_summary + 每日 description；失败时原样返回。"""
    prompt = render_prose_prompt(
        plan=plan, phase_rationale=phase_rationale,
        phase_value=phase_value,
        physiology_summary=physiology_summary, violations=violations,
    )
    try:
        response = client.models.generate_content(
            model=model, contents=prompt,
        )
        env = _parse_envelope(response.text)
        if env is None:
            raise RuntimeError("prose envelope parse failed")
        LOG.event(
            action="prose_generate", status="ok",
            prompt_token_count=getattr(response.usage_metadata,
                                       "prompt_token_count", 0),
            completion_token_count=getattr(response.usage_metadata,
                                           "candidates_token_count", 0),
        )
        return _apply_envelope(plan, env)
    except Exception as e:
        LOG.event(action="prose_generate", status="error", error=str(e))
        return plan.model_copy(update={"coaching_summary": FALLBACK_COACH})
```

- [ ] **Step 5: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_prose_generator.py -v`
Expected: PASS all four.

- [ ] **Step 6: Commit**

```bash
git add icu/prompts/session_designer/prose_prompt.md \
        icu/src/coach/session_designer/prose_generator.py \
        icu/tests/unit/session_designer/test_prose_generator.py
git commit -m "feat(coach-phase2): Gemini prose generator (structured→narrative with numeric-field guard)"
```

---

## Task 44: Save plan files (json + md)

**Goal:** 一个 `save_weekly_plan()` 函数：给出 `WeeklyPlan`、`week_start` 日期、输出目录，生成两份文件（沿用 legacy 命名）：
- `reports/plan_YYYYMMDD.json` — `plan.model_dump()` 扁平化
- `reports/plan_YYYYMMDD.md` — markdown table + 每日 description

**Files:**
- Modify: `icu/src/coach/session_designer/prose_generator.py`（append `save_weekly_plan`）
- Create: `icu/tests/unit/session_designer/test_save_plan.py`

- [ ] **Step 1: Write failing test**

Write `icu/tests/unit/session_designer/test_save_plan.py`:
```python
import json
from datetime import date
from pathlib import Path

from src.coach.session_designer.prose_generator import save_weekly_plan
from src.coach.session_designer.types import DayPlanV2, WeeklyPlan


def _plan():
    days = [
        DayPlanV2(date="2026-04-20", day_of_week="Mon",
                  training_type="Rest", icu_type="Rest",
                  name="Rest", description="完全休息",
                  duration_min=0, target_tss=0),
    ] + [
        DayPlanV2(date=f"2026-04-{d}", day_of_week=dow,
                  training_type="Aerobic", icu_type="Ride",
                  name=f"Z2 day {d}", description="保持 Z2",
                  duration_min=60, target_tss=45)
        for d, dow in [(21,"Tue"),(22,"Wed"),(23,"Thu"),(24,"Fri"),(25,"Sat"),(26,"Sun")]
    ]
    return WeeklyPlan(
        week_start="2026-04-20", week_end="2026-04-26",
        focus_theme="BUILD week", weekly_tss_target=300,
        coaching_summary="本周 build 周 1/4，维持 Z2 基础。",
        days=days,
    )


def test_save_weekly_plan_produces_json_and_md(tmp_path):
    plan = _plan()
    paths = save_weekly_plan(
        plan=plan, out_dir=tmp_path, week_start=date(2026, 4, 20),
    )
    assert Path(paths["json"]).exists()
    assert Path(paths["md"]).exists()
    doc = json.loads(Path(paths["json"]).read_text())
    assert doc["week_start"] == "2026-04-20"
    assert len(doc["days"]) == 7
    md = Path(paths["md"]).read_text(encoding="utf-8")
    assert "本周 build 周" in md
    assert "Z2" in md
    # Markdown 表格行数：标题 + 分隔 + 7 天
    table_lines = [ln for ln in md.splitlines() if ln.startswith("|")]
    assert len(table_lines) >= 9


def test_save_weekly_plan_overwrites(tmp_path):
    plan = _plan()
    save_weekly_plan(plan, tmp_path, date(2026, 4, 20))
    plan2 = plan.model_copy(update={"coaching_summary": "updated"})
    paths = save_weekly_plan(plan2, tmp_path, date(2026, 4, 20))
    md = Path(paths["md"]).read_text(encoding="utf-8")
    assert "updated" in md
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — function undefined.

- [ ] **Step 3: Implement save_weekly_plan**

Append to `icu/src/coach/session_designer/prose_generator.py`:
```python
from datetime import date as DateT  # add to existing imports if not present


def _render_markdown(plan: WeeklyPlan) -> str:
    lines = [
        f"# 训练计划 — {plan.week_start} 至 {plan.week_end}\n",
        f"**主题**: {plan.focus_theme}",
        f"**周 TSS 目标**: {plan.weekly_tss_target}\n",
        f"## 教练说\n\n{plan.coaching_summary}\n",
        "## 7 天计划\n",
        "| 日期 | 星期 | 类型 | 训练 | 时长 | TSS | 功率/心率 |",
        "|------|------|------|------|------|-----|----------|",
    ]
    for d in plan.days:
        power = d.power_range_w or d.hr_range_bpm or "-"
        lines.append(
            f"| {d.date} | {d.day_of_week} | {d.training_type} | "
            f"{d.name} | {d.duration_min}min | {d.target_tss} | {power} |"
        )
    lines.append("\n## 详细说明\n")
    for d in plan.days:
        lines.append(f"### {d.date} {d.day_of_week} — {d.name}\n")
        lines.append(d.description + "\n")
    return "\n".join(lines)


def save_weekly_plan(
    plan: WeeklyPlan, out_dir: Path, week_start: DateT
) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tag = week_start.strftime("%Y%m%d")
    json_path = out / f"plan_{tag}.json"
    md_path = out / f"plan_{tag}.md"
    json_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(plan), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}
```

- [ ] **Step 4: Run — pass**

Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_save_plan.py -v`
Expected: PASS both.

- [ ] **Step 5: Commit**

```bash
git add icu/src/coach/session_designer/prose_generator.py \
        icu/tests/unit/session_designer/test_save_plan.py
git commit -m "feat(coach-phase2): save_weekly_plan (json + md reports, legacy-compatible filenames)"
```

---

## End-of-file checkpoint

- [ ] `pytest tests/unit/ -v` 全绿
- [ ] 3 次提交（T43 prompt + T43 code / T44）
- [ ] 运行 `save-progress`
- [ ] 结束 session。下一个 session 从 [`10-integration.md`](./10-integration.md) 开始。
