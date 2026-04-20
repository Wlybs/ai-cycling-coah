"""Unit tests for periodization_audit.py."""
import json
from datetime import date
from pathlib import Path

import pytest

from src.coach.periodization.types import (
    DayIntent, IntensityTier, MacroPlan, MacroWindow, MesoBlock, MicroCycle,
    NextRace, Phase, PhaseIntent, PeriodizationSnapshot,
)
from scripts.periodization_audit import main as audit_main


def _seed_snapshot(mem: Path):
    """Create a minimal valid PeriodizationSnapshot for testing."""
    p = mem / "periodization"
    p.mkdir(parents=True, exist_ok=True)
    intent = PhaseIntent(
        phase=Phase.BUILD, primary_adaptation="threshold_capacity",
        weekly_tss_target=525,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )
    macro = MacroPlan(
        generated_at="2026-04-18T00:00:00Z",
        season_end_date=date(2026, 9, 30),
        windows=[MacroWindow(phase=Phase.BUILD,
                             start_date=date(2026, 4, 13),
                             end_date=date(2026, 5, 10), intent=intent)],
    )
    meso = MesoBlock(pattern="3:1",
                     block_start=date(2026, 4, 13),
                     block_end=date(2026, 5, 10),
                     weekly_load_multipliers=[1.0, 1.05, 1.10, 0.70],
                     phase=Phase.BUILD)
    micro = MicroCycle(
        week_start=date(2026, 4, 20), week_end=date(2026, 4, 26),
        phase=Phase.BUILD, intent=intent,
        days=[DayIntent(day_of_week=d, tier=IntensityTier.EASY,
                        target_tss=40, session_hint="z2")
              for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]],
        weekly_tss_target=525,
    )
    snap = PeriodizationSnapshot(
        generated_at="2026-04-18T00:00:00Z",
        current_phase=Phase.BUILD, macro=macro, meso=meso, micro=micro,
        next_race=NextRace(name="Goal", race_date=date(2026, 6, 15),
                           priority="A"),
    )
    (p / "periodization_current.json").write_text(
        snap.model_dump_json(), encoding="utf-8")


def test_audit_prints_phase_and_macro_and_micro(tmp_path, capsys):
    """Test that audit prints phase, race name, dates, and all 7 days."""
    mem = tmp_path / "coach_memory"
    _seed_snapshot(mem)
    audit_main(memory_dir=mem)
    out = capsys.readouterr().out
    assert "BUILD" in out
    assert "Goal" in out
    # Macro line contains date
    assert "2026-04-13" in out
    # Micro table has all 7 days
    for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
        assert d in out


def test_audit_handles_missing_snapshot(tmp_path, capsys):
    """Test that audit gracefully handles missing snapshot."""
    audit_main(memory_dir=tmp_path / "nope")
    out = capsys.readouterr().out
    assert ("no snapshot" in out.lower() or "缺失" in out or
            "missing" in out.lower())
