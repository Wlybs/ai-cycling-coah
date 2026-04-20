"""Unit tests for plan_preview.py."""
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.plan_preview import main as preview_main
from src.coach.session_designer.generator_v2 import GeneratePlanV2Result


def test_plan_preview_prints_table_for_happy_path(tmp_path, capsys):
    """Test that plan_preview prints a table with days and TSS."""
    reports = tmp_path / "reports"

    # Create a minimal valid WeeklyPlan JSON
    plan_json = {
        "week_start": "2026-04-20",
        "week_end": "2026-04-26",
        "focus_theme": "BUILD",
        "weekly_tss_target": 525,
        "days": [
            {
                "day_of_week": "Mon",
                "training_type": "Recovery",
                "name": "Easy spin",
                "duration_min": 45,
                "target_tss": 40,
                "power_range_w": "120-160W",
            },
            {
                "day_of_week": "Tue",
                "training_type": "Threshold",
                "name": "Tempo intervals",
                "duration_min": 75,
                "target_tss": 90,
                "power_range_w": "240-260W",
            },
            {
                "day_of_week": "Wed",
                "training_type": "Recovery",
                "name": "Easy ride",
                "duration_min": 60,
                "target_tss": 45,
                "power_range_w": "120-160W",
            },
            {
                "day_of_week": "Thu",
                "training_type": "VO2max",
                "name": "VO2 repeats",
                "duration_min": 60,
                "target_tss": 85,
                "power_range_w": "280-310W",
            },
            {
                "day_of_week": "Fri",
                "training_type": "Recovery",
                "name": "Shakeout",
                "duration_min": 45,
                "target_tss": 35,
                "hr_range_bpm": "120-140",
            },
            {
                "day_of_week": "Sat",
                "training_type": "Aerobic",
                "name": "Long ride",
                "duration_min": 120,
                "target_tss": 150,
                "power_range_w": "160-200W",
            },
            {
                "day_of_week": "Sun",
                "training_type": "Rest",
                "name": "Rest",
                "duration_min": 0,
                "target_tss": 0,
                "power_range_w": None,
            },
        ],
    }

    plan_json_path = reports / "plan_20260420.json"
    reports.mkdir(parents=True, exist_ok=True)
    plan_json_path.write_text(json.dumps(plan_json), encoding="utf-8")

    result = GeneratePlanV2Result(
        status="ok",
        plan_json_path=str(plan_json_path),
        plan_md_path=str(reports / "plan_20260420.md"),
        trace_path=str(reports / "plan_20260420.trace.json"),
        prose_prompt_path=str(reports / "plan_20260420.prose_prompt.md"),
        violations=[],
    )

    with patch("scripts.plan_preview.generate_plan_v2", return_value=result):
        preview_main(week_start_iso="2026-04-20")

    out = capsys.readouterr().out
    assert "WeeklyPlan" in out or "计划" in out or "Plan" in out
    assert "TSS" in out
    for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
        assert d in out


def test_plan_preview_shows_violations_when_present(tmp_path, capsys):
    """Test that plan_preview displays violations."""
    reports = tmp_path / "reports"

    plan_json = {
        "week_start": "2026-04-20",
        "week_end": "2026-04-26",
        "focus_theme": "BUILD",
        "weekly_tss_target": 525,
        "days": [
            {
                "day_of_week": "Mon",
                "training_type": "Recovery",
                "name": "Easy",
                "duration_min": 45,
                "target_tss": 40,
                "power_range_w": "120-160W",
            },
        ] + [
            {
                "day_of_week": d,
                "training_type": "Rest",
                "name": "Rest",
                "duration_min": 0,
                "target_tss": 0,
                "power_range_w": None,
            }
            for d in ["Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        ],
    }

    plan_json_path = reports / "plan_20260420.json"
    reports.mkdir(parents=True, exist_ok=True)
    plan_json_path.write_text(json.dumps(plan_json), encoding="utf-8")

    result = GeneratePlanV2Result(
        status="ok",
        plan_json_path=str(plan_json_path),
        plan_md_path=str(reports / "plan_20260420.md"),
        trace_path=str(reports / "plan_20260420.trace.json"),
        prose_prompt_path=str(reports / "plan_20260420.prose_prompt.md"),
        violations=[
            {
                "rule": "rest_violation",
                "message": "Insufficient rest days",
                "suggested_action": "Add more rest",
            }
        ],
    )

    with patch("scripts.plan_preview.generate_plan_v2", return_value=result):
        preview_main(week_start_iso="2026-04-20")

    out = capsys.readouterr().out
    assert ("未解决护栏" in out or "violation" in out.lower() or
            "rest_violation" in out)
