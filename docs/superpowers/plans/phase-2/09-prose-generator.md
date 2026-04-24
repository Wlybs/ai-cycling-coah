# Phase 2 — Prose I/O (Tasks T43–T44) — Revised 2026-04-19

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Supersedes** the original `09-prose-generator.md` committed at `4fa3f14`. See spec [`../../specs/2026-04-19-phase-2-file-09-redesign.md`](../../specs/2026-04-19-phase-2-file-09-redesign.md) for the full design rationale.

**Goal:** Produce the API-free prose pipeline for Phase 2: `save_weekly_plan` emits the 4-file output set (`.json` / `.md` / `.trace.json` / `.prose_prompt.md`), and `prose_io` lets the user round-trip an LLM response back into the plan with a two-layer numeric-field guard. No `google.genai` client is imported anywhere.

**Architecture:** One file for filesystem IO (`plan_writer.py`), one file for prompt rendering + response merging (`prose_io.py`). `save_weekly_plan` always writes `.json` + `.md`; `.trace.json` and `.prose_prompt.md` are written only when the caller supplies them. `apply_prose_response` parses user-pasted JSON through a strict Pydantic model that ignores unknown fields, then merges `coaching_summary` + per-day `description` via `model_copy(update={...})` — numeric fields are structurally unreachable from the merge path.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest. No new external deps.

**Files covered:**
- `icu/src/coach/session_designer/plan_writer.py` (new)
- `icu/src/coach/session_designer/prose_io.py` (new)
- `icu/prompts/session_designer/prose_prompt.md` (new)
- `icu/tests/unit/session_designer/test_plan_writer.py` (new)
- `icu/tests/unit/session_designer/test_prose_io.py` (new)
- `docs/superpowers/plans/phase-2/10-integration.md` (doc sync — see final section)

**Deleted vs original plan:** no `prose_generator.py`, no `enrich_with_prose`, no mocked-Gemini tests, no `google.genai` import.

**Notable divergence from spec (§load_and_apply_prose):** the spec said `load_and_apply_prose` rewrites all 4 files. In this plan it rewrites only `.json` + `.md` — `.trace.json` and `.prose_prompt.md` represent pre-enrichment artifacts (the prompt was already used; the trace is from composer/assembler and did not change). This avoids needing physiology context at apply-time and keeps the CLI flag narrow. Reflected in test design.

---

## Task 43: `plan_writer.py` — four-artifact output

**Files:**
- Create: `icu/prompts/session_designer/prose_prompt.md`
- Create: `icu/src/coach/session_designer/plan_writer.py`
- Create: `icu/tests/unit/session_designer/test_plan_writer.py`

### Step 1: Write prompt template

- [ ] Create `icu/prompts/session_designer/prose_prompt.md`:

```markdown
# 角色
你是一位顶尖职业自行车教练，正在把结构化周训练方案翻译成中文叙述性解读。

# 约束（绝对不能违反）
- 禁止修改 plan.days[*].duration_min / target_tss / power_range_w / hr_range_bpm / name / training_type / icu_type。
- 你只填充：coaching_summary（整周叙述），以及每一天的 description（替换为更有深度的教练语言，但字段保留）。
- 每日 description 必须覆盖：主集强度目的、本日 fueling 要点（若是长骑或 hard 日）、与本周 PhaseIntent 的关系。
- 100% 用中文，但核心名词保留英文（CP、W'、VO2max、Z4 等）。
- 如有 violations_remaining，必须在 coaching_summary 里用一句话解释为什么没有完美规避。

# 输出 JSON schema（严格）
{
  "coaching_summary": str,          // 150-400 字
  "days": [
    {"date": "YYYY-MM-DD", "description": str},   // 每日 60-180 字
    ... (恰好 7 条，date 必须与输入 plan.days 的 date 一一对应)
  ]
}

# 注意
- 只输出上述 JSON。不要 markdown 围栏、不要解释文字、不要示例输出。
- 数字字段（duration_min 等）即使你觉得更合理，也不要出现在返回里——脚本会自动丢弃。
```

### Step 2: Write failing tests

- [ ] Create `icu/tests/unit/session_designer/test_plan_writer.py`:

```python
"""T43 — plan_writer tests."""
from __future__ import annotations

import json
from pathlib import Path

from src.coach.session_designer.plan_writer import save_weekly_plan
from src.coach.session_designer.types import DayPlanV2, WeeklyPlan


def _plan(**overrides) -> WeeklyPlan:
    days = [
        DayPlanV2(
            date="2026-04-20", day_of_week="Mon",
            training_type="Rest", icu_type="Rest",
            name="Rest", description="完全休息",
            duration_min=0, target_tss=0,
        ),
        DayPlanV2(
            date="2026-04-21", day_of_week="Tue",
            training_type="VO2max", icu_type="Ride",
            name="VO2max 5x4", description="skeleton",
            duration_min=75, target_tss=95,
            power_range_w="308-322W",
        ),
    ] + [
        DayPlanV2(
            date=f"2026-04-{d}", day_of_week=dow,
            training_type="Aerobic", icu_type="Ride",
            name=f"Z2 day {d}", description="保持 Z2",
            duration_min=60, target_tss=45,
            hr_range_bpm="130-145bpm",
        )
        for d, dow in [(22, "Wed"), (23, "Thu"), (24, "Fri"), (25, "Sat"), (26, "Sun")]
    ]
    base = dict(
        week_start="2026-04-20",
        week_end="2026-04-26",
        focus_theme="BUILD week — threshold_capacity",
        weekly_tss_target=500,
        days=days,
    )
    base.update(overrides)
    return WeeklyPlan(**base)


_PROMPT_STUB = "# 角色\n你是教练。\n\n# 输入\nCP=280W\n"
_TRACE_STUB = {"composer": "stub", "assembler": "stub"}


def test_save_weekly_plan_emits_all_four_artifacts(tmp_path):
    plan = _plan()
    paths = save_weekly_plan(
        plan=plan, out_dir=tmp_path,
        prose_prompt=_PROMPT_STUB, trace=_TRACE_STUB,
    )
    assert set(paths.keys()) == {"json", "md", "trace", "prose_prompt"}
    for p in paths.values():
        assert Path(p).exists()

    doc = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert doc["week_start"] == "2026-04-20"
    assert len(doc["days"]) == 7

    md = Path(paths["md"]).read_text(encoding="utf-8")
    assert "BUILD week" in md
    table_lines = [ln for ln in md.splitlines() if ln.startswith("|")]
    assert len(table_lines) >= 9  # header + separator + 7 day rows

    trace = json.loads(Path(paths["trace"]).read_text(encoding="utf-8"))
    assert trace["composer"] == "stub"

    pp = Path(paths["prose_prompt"]).read_text(encoding="utf-8")
    assert "教练" in pp


def test_save_weekly_plan_writes_only_json_and_md_when_optional_args_missing(tmp_path):
    plan = _plan()
    paths = save_weekly_plan(plan=plan, out_dir=tmp_path)
    assert set(paths.keys()) == {"json", "md"}
    assert not (tmp_path / "plan_20260420.trace.json").exists()
    assert not (tmp_path / "plan_20260420.prose_prompt.md").exists()


def test_save_weekly_plan_is_utf8_and_idempotent_on_rewrite(tmp_path):
    plan = _plan()
    save_weekly_plan(
        plan=plan, out_dir=tmp_path,
        prose_prompt=_PROMPT_STUB, trace=_TRACE_STUB,
    )
    plan2 = plan.model_copy(update={"coaching_summary": "升级版教练文案"})
    paths = save_weekly_plan(
        plan=plan2, out_dir=tmp_path,
        prose_prompt=_PROMPT_STUB, trace=_TRACE_STUB,
    )
    md = Path(paths["md"]).read_text(encoding="utf-8")
    assert "升级版教练文案" in md
    assert "完全休息" in md  # utf-8 round-trip of a day description


def test_markdown_table_includes_power_or_hr_range(tmp_path):
    plan = _plan()
    paths = save_weekly_plan(
        plan=plan, out_dir=tmp_path,
        prose_prompt=_PROMPT_STUB, trace=_TRACE_STUB,
    )
    md = Path(paths["md"]).read_text(encoding="utf-8")
    # Rest day → "-" in power/HR column
    assert "| 2026-04-20 | Mon | Rest | Rest | 0min | 0 | - |" in md
    # Ride day with power_range_w
    assert "308-322W" in md
    # Ride day with hr_range_bpm only
    assert "130-145bpm" in md
```

### Step 3: Run — expect FAIL

- [ ] Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_plan_writer.py -v`

  Expected: FAIL — `ModuleNotFoundError: No module named 'src.coach.session_designer.plan_writer'`.

### Step 4: Implement `plan_writer.py`

- [ ] Create `icu/src/coach/session_designer/plan_writer.py`:

```python
"""Phase 2 File 09 — filesystem output for the WeeklyPlan pipeline.

Emits up to 4 artifacts under out_dir:
- plan_YYYYMMDD.json          canonical structured plan (push source)
- plan_YYYYMMDD.md            skeleton readable markdown
- plan_YYYYMMDD.trace.json    physiology / composer trace (if caller passes `trace`)
- plan_YYYYMMDD.prose_prompt.md  ready-to-paste LLM prompt (if caller passes `prose_prompt`)

No LLM API call anywhere in this module.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .types import WeeklyPlan


def _render_markdown(plan: WeeklyPlan) -> str:
    summary = plan.coaching_summary or "（skeleton — 未经 LLM 叙述增强）"
    lines = [
        f"# 训练计划 — {plan.week_start} 至 {plan.week_end}\n",
        f"**主题**: {plan.focus_theme}",
        f"**周 TSS 目标**: {plan.weekly_tss_target}\n",
        f"## 教练说\n\n{summary}\n",
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
    plan: WeeklyPlan,
    out_dir: Path,
    prose_prompt: str | None = None,
    trace: dict | None = None,
) -> dict[str, Path]:
    """Write plan artifacts. Overwrites any existing files with the same tag.

    Filename tag is derived from plan.week_start (ISO date string) so the
    on-disk filename and the JSON content can never drift apart.

    .json and .md are always written. .trace.json and .prose_prompt.md are
    written only when the corresponding argument is not None — this lets
    `apply_prose_response` reuse this function to rewrite only the prose
    outputs without touching the trace or prompt artifacts.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tag = date.fromisoformat(plan.week_start).strftime("%Y%m%d")

    paths: dict[str, Path] = {
        "json": out / f"plan_{tag}.json",
        "md": out / f"plan_{tag}.md",
    }
    paths["json"].write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    paths["md"].write_text(_render_markdown(plan), encoding="utf-8")

    if trace is not None:
        paths["trace"] = out / f"plan_{tag}.trace.json"
        paths["trace"].write_text(
            json.dumps(trace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if prose_prompt is not None:
        paths["prose_prompt"] = out / f"plan_{tag}.prose_prompt.md"
        paths["prose_prompt"].write_text(prose_prompt, encoding="utf-8")
    return paths
```

### Step 5: Run — expect PASS

- [ ] Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_plan_writer.py -v`

  Expected: PASS all 4 tests.

### Step 6: Commit

- [ ] Run:

```bash
git add icu/prompts/session_designer/prose_prompt.md \
        icu/src/coach/session_designer/plan_writer.py \
        icu/tests/unit/session_designer/test_plan_writer.py
git commit -m "feat(coach-phase2): T43 plan_writer — 4-artifact weekly plan output (API-free)"
```

---

## Task 44: `prose_io.py` — prompt render + response merge

**Files:**
- Create: `icu/src/coach/session_designer/prose_io.py`
- Create: `icu/tests/unit/session_designer/test_prose_io.py`

### Step 1: Write failing tests

- [ ] Create `icu/tests/unit/session_designer/test_prose_io.py`:

```python
"""T44 — prose_io tests (API-free)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.coach.session_designer.plan_writer import save_weekly_plan
from src.coach.session_designer.prose_io import (
    apply_prose_response,
    load_and_apply_prose,
    render_prose_prompt,
)
from src.coach.session_designer.types import DayPlanV2, WeeklyPlan


def _plan() -> WeeklyPlan:
    days = [
        DayPlanV2(
            date="2026-04-20", day_of_week="Mon",
            training_type="Rest", icu_type="Rest",
            name="Rest", description="完全休息",
            duration_min=0, target_tss=0,
        ),
        DayPlanV2(
            date="2026-04-21", day_of_week="Tue",
            training_type="VO2max", icu_type="Ride",
            name="VO2max 5x4", description="skeleton",
            duration_min=75, target_tss=95,
            power_range_w="308-322W",
        ),
    ] + [
        DayPlanV2(
            date=f"2026-04-{d}", day_of_week=dow,
            training_type="Aerobic", icu_type="Ride",
            name=f"Z2 day {d}", description="保持 Z2",
            duration_min=60, target_tss=45,
            hr_range_bpm="130-145bpm",
        )
        for d, dow in [(22, "Wed"), (23, "Thu"), (24, "Fri"), (25, "Sat"), (26, "Sun")]
    ]
    return WeeklyPlan(
        week_start="2026-04-20",
        week_end="2026-04-26",
        focus_theme="BUILD week — threshold_capacity",
        weekly_tss_target=500,
        coaching_summary="",
        days=days,
    )


def _response(**overrides) -> dict:
    base = {
        "coaching_summary": "本周 BUILD 周，重点 threshold_capacity。" * 4,
        "days": [
            {"date": "2026-04-20", "description": "恢复日：完全休息或 30min 散步。"},
            {"date": "2026-04-21", "description": "VO2max 5×4min — 目标打开心肺上限。"},
            {"date": "2026-04-22", "description": "Z2 60min — 有氧基础维持。"},
            {"date": "2026-04-23", "description": "Z2 60min — 保持节奏。"},
            {"date": "2026-04-24", "description": "Z2 60min — 低压力保底。"},
            {"date": "2026-04-25", "description": "Z2 60min — 周末长骑前铺垫。"},
            {"date": "2026-04-26", "description": "Z2 60min — 结束本周基础量。"},
        ],
    }
    base.update(overrides)
    return base


def test_render_prose_prompt_mentions_all_required_context():
    plan = _plan()
    prompt = render_prose_prompt(
        plan=plan,
        phase_rationale="Allen-Coggan BUILD week 1/4",
        phase_value="BUILD",
        physiology_summary={
            "cp": 280, "w_prime": 22000,
            "durability_60s_pct": 3.0, "knee_flag": None,
        },
        violations=[],
    )
    assert "BUILD" in prompt
    assert "CP=280W" in prompt
    assert "threshold_capacity" in prompt
    assert "禁止修改" in prompt
    assert "Allen-Coggan" in prompt


def test_apply_prose_response_fills_summary_and_descriptions():
    plan = _plan()
    result = apply_prose_response(plan, _response())
    assert result.coaching_summary.startswith("本周 BUILD 周")
    tue = [d for d in result.days if d.day_of_week == "Tue"][0]
    assert tue.description == "VO2max 5×4min — 目标打开心肺上限。"


def test_apply_prose_response_does_not_mutate_numeric_fields():
    plan = _plan()
    malicious = _response()
    malicious["days"][1] = {
        "date": "2026-04-21",
        "description": "custom",
        "duration_min": 9999,          # should be dropped by _ProseDay.extra=ignore
        "power_range_w": "999-9999W",  # should be dropped
        "target_tss": 1,               # should be dropped
    }
    result = apply_prose_response(plan, malicious)
    tue = [d for d in result.days if d.day_of_week == "Tue"][0]
    assert tue.duration_min == 75           # original preserved
    assert tue.target_tss == 95             # original preserved
    assert tue.power_range_w == "308-322W"  # original preserved
    assert tue.description == "custom"      # text field accepted


def test_apply_prose_response_rejects_day_count_mismatch():
    plan = _plan()
    short = _response()
    short["days"] = short["days"][:6]  # only 6 days
    with pytest.raises(ValueError, match="exactly 7 days"):
        apply_prose_response(plan, short)


def test_apply_prose_response_rejects_date_mismatch():
    plan = _plan()
    wrong = _response()
    wrong["days"][6] = {"date": "2026-04-27", "description": "out-of-week"}
    with pytest.raises(ValueError, match="date set mismatch"):
        apply_prose_response(plan, wrong)


def test_load_and_apply_prose_rewrites_json_and_md_in_place(tmp_path):
    plan = _plan()
    saved = save_weekly_plan(
        plan=plan, out_dir=tmp_path,
        prose_prompt="original prompt", trace={"composer": "v1"},
    )

    response_path = tmp_path / "prose_response.json"
    response_path.write_text(
        json.dumps(_response(), ensure_ascii=False), encoding="utf-8"
    )

    out = load_and_apply_prose(
        plan_path=saved["json"],
        response_path=response_path,
        out_dir=tmp_path,
    )
    # Only json + md returned (trace & prompt left untouched from initial save)
    assert set(out.keys()) == {"json", "md"}

    doc = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
    assert doc["coaching_summary"].startswith("本周 BUILD 周")
    tue = [d for d in doc["days"] if d["day_of_week"] == "Tue"][0]
    assert tue["description"] == "VO2max 5×4min — 目标打开心肺上限。"
    assert tue["duration_min"] == 75  # numeric untouched across the round-trip

    md = Path(out["md"]).read_text(encoding="utf-8")
    assert "本周 BUILD 周" in md

    # Pre-existing trace + prose_prompt still on disk, untouched
    assert (tmp_path / "plan_20260420.trace.json").exists()
    assert (tmp_path / "plan_20260420.prose_prompt.md").read_text(
        encoding="utf-8"
    ) == "original prompt"
```

### Step 2: Run — expect FAIL

- [ ] Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_prose_io.py -v`

  Expected: FAIL — `ModuleNotFoundError: No module named 'src.coach.session_designer.prose_io'`.

### Step 3: Implement `prose_io.py`

- [ ] Create `icu/src/coach/session_designer/prose_io.py`:

```python
"""Phase 2 File 09 — prose prompt rendering + user response merge.

No LLM API call. `render_prose_prompt` builds the text the user pastes into
Claude Code / Gemini CLI. `apply_prose_response` merges the user's pasted
JSON back into the WeeklyPlan with a two-layer numeric-field guard:

1. `_ProseResponse` / `_ProseDay` ignore any field other than
   `coaching_summary` and `days[*].{date, description}`, so malicious numeric
   fields are dropped at parse time.
2. The merge itself uses `model_copy(update={...})` on only those two text
   fields, so no numeric field is structurally reachable from the merge path.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .plan_writer import save_weekly_plan
from .types import WeeklyPlan

PROMPT_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "prompts" / "session_designer" / "prose_prompt.md"
)


class _ProseDay(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: str
    description: str


class _ProseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    coaching_summary: str
    days: list[_ProseDay]


def _load_prompt_template() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def render_prose_prompt(
    plan: WeeklyPlan,
    phase_rationale: str,
    phase_value: str,
    physiology_summary: dict,
    violations: list,
) -> str:
    base = _load_prompt_template()
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


def apply_prose_response(
    plan: WeeklyPlan,
    response: dict,
) -> WeeklyPlan:
    env = _ProseResponse.model_validate(response)
    if len(env.days) != 7:
        raise ValueError(
            f"prose response must have exactly 7 days, got {len(env.days)}"
        )
    plan_dates = {d.date for d in plan.days}
    response_dates = {d.date for d in env.days}
    if plan_dates != response_dates:
        missing = sorted(plan_dates - response_dates)
        extra = sorted(response_dates - plan_dates)
        raise ValueError(
            f"prose response date set mismatch. "
            f"missing={missing} extra={extra}"
        )
    by_date = {d.date: d for d in env.days}
    new_days = [
        day.model_copy(update={"description": by_date[day.date].description})
        for day in plan.days
    ]
    return plan.model_copy(update={
        "coaching_summary": env.coaching_summary,
        "days": new_days,
    })


def load_and_apply_prose(
    plan_path: Path,
    response_path: Path,
    out_dir: Path,
) -> dict[str, Path]:
    """Read plan.json + response.json, merge prose into plan, and overwrite
    plan_YYYYMMDD.{json,md} only. The `.trace.json` and `.prose_prompt.md`
    from the initial save are intentionally left untouched — they represent
    pre-enrichment artifacts whose content does not change with prose merge.
    """
    plan = WeeklyPlan.model_validate_json(
        Path(plan_path).read_text(encoding="utf-8")
    )
    response_doc = json.loads(Path(response_path).read_text(encoding="utf-8"))
    enriched = apply_prose_response(plan, response_doc)
    return save_weekly_plan(
        plan=enriched,
        out_dir=out_dir,
        # prose_prompt=None, trace=None → only .json + .md get rewritten
    )
```

### Step 4: Run — expect PASS

- [ ] Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/test_prose_io.py -v`

  Expected: PASS all 6 tests.

### Step 5: Full regression

- [ ] Run: `cd icu && .venv/bin/pytest tests/unit/session_designer/ -v`

  Expected: PASS both test files (10 tests total across T43 + T44).

### Step 6: Grep guard — no Gemini leak

- [ ] Run:

```bash
cd icu && grep -r "google.genai" src/coach/session_designer/ || echo "OK: no google.genai import"
cd icu && grep -r "generate_content" src/coach/session_designer/ || echo "OK: no generate_content call"
```

  Expected output: `OK: no google.genai import` and `OK: no generate_content call`.

### Step 7: Commit

- [ ] Run:

```bash
git add icu/src/coach/session_designer/prose_io.py \
        icu/tests/unit/session_designer/test_prose_io.py
git commit -m "feat(coach-phase2): T44 prose_io — API-free prompt render + response merge with numeric guard"
```

---

## Doc sync: Patch `10-integration.md`

Because File 10 currently references `enrich_with_prose(client=gemini_client, ...)`, patch it now so the next session delivering File 10 starts from a correct spec. No test changes. One commit.

### Step 1: Open `docs/superpowers/plans/phase-2/10-integration.md`

- [ ] Search for any of these strings: `enrich_with_prose`, `gemini_client`, `google.genai`, `generate_content`.

### Step 2: Replace the Gemini call block with the API-free flow

In the body of T46 (push_plan integration), replace the code that constructs a Gemini client and calls `enrich_with_prose(...)` with:

```python
from src.coach.session_designer.plan_writer import save_weekly_plan
from src.coach.session_designer.prose_io import (
    render_prose_prompt,
    load_and_apply_prose,
)


def generate_plan_v2(week_start: date, week_end: date) -> dict[str, Path]:
    snapshot = load_periodization_snapshot(...)  # from File 05
    plan = assemble_weekly(snapshot, ...)        # from File 08
    prompt = render_prose_prompt(
        plan=plan,
        phase_rationale=snapshot.micro.phase_rationale,
        phase_value=snapshot.micro.phase.value,
        physiology_summary=_summarize_physiology(),  # CP/W'/durability/knee
        violations=plan.violations_remaining,
    )
    trace = build_trace(plan, snapshot)          # from File 08
    paths = save_weekly_plan(
        plan=plan, out_dir=Path("reports"),
        prose_prompt=prompt, trace=trace,
    )
    print(f"✅ 骨架计划已写入 {paths['json']}")
    print(f"📝 如需教练叙述：复制 {paths['prose_prompt']} 到 Claude Code，")
    print(f"    保存返回 JSON 后运行 --apply-prose --plan-file {paths['json']} --prose-response <path>")
    return paths


def apply_prose_to_existing(plan_path: Path, response_path: Path) -> dict[str, Path]:
    return load_and_apply_prose(
        plan_path=plan_path,
        response_path=response_path,
        out_dir=plan_path.parent,
    )
```

### Step 3: Update the T46 argparse block in `push_plan.py` section

Replace whatever flag set the old plan described with:

| Flag | Purpose |
|------|---------|
| `--engine v2` | Run `generate_plan_v2`. Default stays legacy. |
| `--apply-prose --plan-file X --prose-response Y` | Merge user-pasted prose into existing plan. Overwrites `X` in place. |
| `--push --plan-file X` | Unchanged. Reads any valid `WeeklyPlan` JSON (skeleton or enriched). |

The fallback guardrail rule is unchanged: any exception inside `generate_plan_v2` is caught and the code falls back to legacy `generate_plan(...)`.

### Step 4: Add revision marker at the top of `10-integration.md`

Insert right under the File 10 title:

```markdown
> **Revised 2026-04-19:** API-free prose flow. No `google.genai` import, no
> `enrich_with_prose` call. Uses `plan_writer.save_weekly_plan` +
> `prose_io.render_prose_prompt` + `prose_io.load_and_apply_prose`.
> See [`../../specs/2026-04-19-phase-2-file-09-redesign.md`](../../specs/2026-04-19-phase-2-file-09-redesign.md).
```

### Step 5: Grep guard on the plan file

- [ ] Run: `grep -E "enrich_with_prose|gemini_client|google\.genai|generate_content" docs/superpowers/plans/phase-2/10-integration.md && echo "❌ stale refs remain" || echo "OK: no stale refs"`

  Expected: `OK: no stale refs`.

### Step 6: Commit

- [ ] Run:

```bash
git add docs/superpowers/plans/phase-2/10-integration.md
git commit -m "docs(coach-phase2): patch File 10 to reference API-free prose_io (File 09 redesign)"
```

---

## End-of-file checkpoint

- [ ] `cd icu && .venv/bin/pytest tests/unit/session_designer/ -v` — all green (10 new tests).
- [ ] `cd icu && .venv/bin/pytest tests/unit/ -v` — full phase-2 suite green (baseline + 10 = 85+).
- [ ] 3 commits on `ai-coach-phase-2`:
  1. `feat(coach-phase2): T43 plan_writer — 4-artifact weekly plan output (API-free)`
  2. `feat(coach-phase2): T44 prose_io — API-free prompt render + response merge with numeric guard`
  3. `docs(coach-phase2): patch File 10 to reference API-free prose_io (File 09 redesign)`
- [ ] No `google.genai` import anywhere under `icu/src/coach/session_designer/`.
- [ ] Run `save-progress` to update memory.
- [ ] End session. Next session starts at [`10-integration.md`](./10-integration.md) (T45–T46), implementing the code now that File 10's plan reflects the API-free API.
