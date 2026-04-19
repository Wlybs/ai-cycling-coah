"""
Tests for the generate_plan_v2 facade (T45).

TDD workflow: test first (RED), then implement (GREEN), then refactor.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from src.coach.session_designer.generator_v2 import (
    GeneratePlanV2Result,
    generate_plan_v2,
)


# === Module-level test fixtures (not pytest fixtures — keep test file self-contained) ===


def _build_warehouse_fixture(tmp_path: Path, ftp: int = 288) -> Path:
    """
    Build a minimal, realistic warehouse fixture with activities + events + wellness + profile.
    Returns path to warehouse root (tmp_path / "icu_data_warehouse").
    """
    wh = tmp_path / "icu_data_warehouse"
    wh.mkdir(parents=True, exist_ok=True)

    # 1_Profile/athlete.json
    profile_dir = wh / "1_Profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "athlete.json").write_text(
        json.dumps({"ftp": ftp, "hr_max": 195, "weight": 62}),
        encoding="utf-8",
    )

    # 2_Activities_Events/activities.json — 18 rides covering week_start - 30 days .. week_start - 1
    activities_dir = wh / "2_Activities_Events"
    activities_dir.mkdir(parents=True, exist_ok=True)
    activities = [
        {
            "id": i,
            "start_date_local": f"2026-03-{21 + i:02d}T09:00:00Z",
            "icu_training_load": 60,
            "distance": 35000,
            "icu_weighted_avg_watts": 210,
            "type": "Ride",
        }
        for i in range(18)
    ]
    (activities_dir / "activities.json").write_text(
        json.dumps(activities), encoding="utf-8"
    )

    # 6_Wellness/wellness.json — array of 18 entries matching activities
    wellness_dir = wh / "6_Wellness"
    wellness_dir.mkdir(parents=True, exist_ok=True)
    wellness = [
        {
            "date": f"2026-03-{21 + i:02d}",
            "resting_heart_rate": 50 + (i % 10),
            "sleep_duration": 8 + (i % 2),
        }
        for i in range(18)
    ]
    (wellness_dir / "wellness.json").write_text(
        json.dumps(wellness), encoding="utf-8"
    )

    # 8_Events/events.json — one RACE at week_start + 56 days
    events_dir = wh / "8_Events"
    events_dir.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "id": "race_1",
            "title": "Spring Hill Climb",
            "date": "2026-06-15",
            "type": "RACE",
        }
    ]
    (events_dir / "events.json").write_text(json.dumps(events), encoding="utf-8")

    return wh


def _build_memory_fixture(tmp_path: Path) -> Path:
    """
    Build a minimal coach memory fixture with physiology snapshots.
    Returns path to memory root (tmp_path / "coach_memory").
    """
    mem = tmp_path / "coach_memory"
    mem.mkdir(parents=True, exist_ok=True)

    # physiology/cp_w_current.json
    phys_dir = mem / "physiology"
    phys_dir.mkdir(parents=True, exist_ok=True)
    (phys_dir / "cp_w_current.json").write_text(
        json.dumps(
            {
                "cp_watts": 280,
                "w_prime_joules": 22000,
                "fit_r_squared": 0.95,
                "athlete_ftp_set": 288,
            }
        ),
        encoding="utf-8",
    )

    # physiology/durability.json
    (phys_dir / "durability.json").write_text(
        json.dumps(
            {
                "decay_rate_pct_per_1000kj": {"60s": 3.0, "300s": 2.0},
                "sample_size_rides": 12,
            }
        ),
        encoding="utf-8",
    )

    # physiology/response_profile.json
    (phys_dir / "response_profile.json").write_text(
        json.dumps(
            {
                "types": {
                    "Threshold": {"tolerance": "MED"},
                    "VO2max": {"tolerance": "LOW"},
                    "Tempo": {"tolerance": "HIGH"},
                },
                "knee_loading": {"flag": "ok"},
            }
        ),
        encoding="utf-8",
    )

    # deep_analysis/ empty
    (mem / "deep_analysis").mkdir(parents=True, exist_ok=True)

    return mem


# === Tests ===


class TestGeneratePlanV2:
    """
    Test suite for generate_plan_v2 facade (T45).
    All tests follow TDD: RED → GREEN → REFACTOR.
    """

    def test_generate_plan_v2_returns_error_when_periodization_fails(self, tmp_path):
        """
        Test 1: When periodization refresh fails, generate_plan_v2 returns error status.
        """
        wh = tmp_path / "wh"
        mem = tmp_path / "mem"
        reports = tmp_path / "reports"
        wh.mkdir()
        mem.mkdir()

        with mock.patch(
            "src.coach.session_designer.generator_v2.periodization_engine.refresh_periodization"
        ) as mock_refresh:
            mock_refresh.return_value = {"status": "error", "error": "forced failure"}

            result = generate_plan_v2(
                week_start=date(2026, 4, 20),
                week_end=date(2026, 4, 26),
                warehouse_dir=wh,
                memory_dir=mem,
                reports_dir=reports,
                push_to_icu=False,
            )

            assert result.status == "error"
            assert "forced failure" in result.error
            assert result.plan_json_path is None
            assert result.trace_path is None

    def test_generate_plan_v2_happy_path(self, tmp_path):
        """
        Test 2: Happy path — warehouse + memory fixtures, valid periodization snapshot,
        plan/trace/prose all written.
        """
        wh = _build_warehouse_fixture(tmp_path, ftp=288)
        mem = _build_memory_fixture(tmp_path)
        reports = tmp_path / "reports"

        result = generate_plan_v2(
            week_start=date(2026, 4, 20),
            week_end=date(2026, 4, 26),
            warehouse_dir=wh,
            memory_dir=mem,
            reports_dir=reports,
            push_to_icu=False,
        )

        assert result.status == "ok"
        assert result.plan_json_path is not None
        assert result.plan_md_path is not None
        assert result.trace_path is not None
        assert result.prose_prompt_path is not None

        # Verify files exist
        assert Path(result.plan_json_path).exists()
        assert Path(result.plan_md_path).exists()
        assert Path(result.trace_path).exists()
        assert Path(result.prose_prompt_path).exists()

        # Verify plan JSON has expected structure
        plan_json = json.loads(Path(result.plan_json_path).read_text(encoding="utf-8"))
        assert "days" in plan_json
        assert len(plan_json["days"]) == 7

        # Verify trace has days and violations_remaining
        trace_json = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
        assert "days" in trace_json
        assert "violations_remaining" in trace_json

    def test_generate_plan_v2_push_to_icu_called_when_flag(self, tmp_path):
        """
        Test 3: When push_to_icu=True, _push_to_icu is called with plan dict.
        """
        wh = _build_warehouse_fixture(tmp_path)
        mem = _build_memory_fixture(tmp_path)
        reports = tmp_path / "reports"

        with mock.patch(
            "src.coach.plan_generator._push_to_icu"
        ) as mock_push:

            result = generate_plan_v2(
                week_start=date(2026, 4, 20),
                week_end=date(2026, 4, 26),
                warehouse_dir=wh,
                memory_dir=mem,
                reports_dir=reports,
                push_to_icu=True,
            )

            assert result.status == "ok"
            mock_push.assert_called_once()
            call_args = mock_push.call_args[0][0]
            assert isinstance(call_args, dict)
            assert "days" in call_args

    def test_generate_plan_v2_missing_snapshot_returns_error(self, tmp_path):
        """
        Test 4: When periodization snapshot is missing after refresh, return error.
        """
        wh = _build_warehouse_fixture(tmp_path)
        mem = tmp_path / "mem"
        reports = tmp_path / "reports"
        mem.mkdir()

        # Don't create the periodization dir — snapshot will be None
        with mock.patch(
            "src.coach.session_designer.generator_v2.periodization_engine.refresh_periodization"
        ) as mock_refresh:
            mock_refresh.return_value = {
                "status": "ok",
                "phase": "BASE",
                "reasons": [],
                "snapshot_path": "x",
            }

            result = generate_plan_v2(
                week_start=date(2026, 4, 20),
                week_end=date(2026, 4, 26),
                warehouse_dir=wh,
                memory_dir=mem,
                reports_dir=reports,
                push_to_icu=False,
            )

            assert result.status == "error"
            assert "snapshot missing" in result.error.lower()

    def test_generate_plan_v2_uses_fallback_ftp_from_profile(self, tmp_path):
        """
        Test 5: Fallback FTP is read from warehouse athlete.json and passed to design_week.
        """
        wh = _build_warehouse_fixture(tmp_path, ftp=295)
        mem = _build_memory_fixture(tmp_path)
        reports = tmp_path / "reports"

        # Spy on design_week to capture fallback_ftp argument
        with mock.patch(
            "src.coach.session_designer.generator_v2.design_week",
            wraps=__import__("src.coach.session_designer.assembler", fromlist=["design_week"]).design_week
        ) as mock_design:
            result = generate_plan_v2(
                week_start=date(2026, 4, 20),
                week_end=date(2026, 4, 26),
                warehouse_dir=wh,
                memory_dir=mem,
                reports_dir=reports,
                push_to_icu=False,
            )

            assert result.status == "ok"
            mock_design.assert_called_once()
            # Check that fallback_ftp kwarg was passed with correct value
            call_kwargs = mock_design.call_args[1]
            assert call_kwargs.get("fallback_ftp") == 295
