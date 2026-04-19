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
    paths = save_weekly_plan(
        plan=plan, out_dir=tmp_path,
    )
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
