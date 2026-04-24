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
