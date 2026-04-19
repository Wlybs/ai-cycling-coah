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
from datetime import date as DateT
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
    week_start: DateT,
    prose_prompt: str | None = None,
    trace: dict | None = None,
) -> dict[str, Path]:
    """Write plan artifacts. Overwrites any existing files with the same tag.

    .json and .md are always written. .trace.json and .prose_prompt.md are
    written only when the corresponding argument is not None — this lets
    `apply_prose_response` reuse this function to rewrite only the prose
    outputs without touching the trace or prompt artifacts.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tag = week_start.strftime("%Y%m%d")

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
