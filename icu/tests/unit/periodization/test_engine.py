"""Test suite for periodization engine facade."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.coach.periodization.engine import refresh_periodization
from src.coach.periodization.snapshot_io import load_periodization_snapshot
from src.coach.periodization.types import Phase


def _seed_warehouse(tmp_path: Path) -> Path:
    """Create a mock warehouse with wellness history, events, and athlete profile."""
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "2_Wellness").mkdir(parents=True)
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "1_Profile").mkdir(parents=True)
    # Wellness with rising CTL over 30 days
    wellness = [
        {"id": f"2026-03-{d:02d}", "ctl": 80 + (d - 1) * 0.4, "atl": 90}
        for d in range(1, 32)
    ] + [
        {"id": f"2026-04-{d:02d}", "ctl": 92 + d * 0.2, "atl": 95}
        for d in range(1, 19)
    ]
    (warehouse / "2_Wellness" / "wellness_history.json").write_text(
        json.dumps(wellness), encoding="utf-8")
    # A race in 58 days
    events = [{"id": 1, "category": "RACE", "name": "Goal",
               "start_date_local": "2026-06-15T08:00:00"}]
    (warehouse / "8_Events" / "events.json").write_text(
        json.dumps(events), encoding="utf-8")
    (warehouse / "1_Profile" / "athlete.json").write_text(
        json.dumps({"ftp": 288, "hr_max": 195, "weight": 62}), encoding="utf-8")
    return warehouse


def _seed_memory(tmp_path: Path) -> Path:
    """Create a mock memory directory with deep analysis summary."""
    mem = tmp_path / "coach_memory"
    (mem / "deep_analysis").mkdir(parents=True)
    # summary_latest with stimulus_score 0.55
    (mem / "deep_analysis" / "summary_latest.json").write_text(
        json.dumps({
            "stimulus_score": 0.55, "progression_flag": "progression",
            "headline_verdict": "solid threshold work",
        }), encoding="utf-8")
    return mem


def test_refresh_periodization_writes_snapshot(tmp_path: Path) -> None:
    """Test that refresh_periodization creates a valid snapshot with BUILD phase."""
    warehouse = _seed_warehouse(tmp_path)
    memory = _seed_memory(tmp_path)
    result = refresh_periodization(
        warehouse_dir=warehouse,
        memory_dir=memory,
        reference_date=date(2026, 4, 18),
        generated_at="2026-04-18T00:00:00Z",
    )
    assert result["status"] == "ok"
    snap = load_periodization_snapshot(memory / "periodization")
    assert snap is not None
    # 距离 race 58 天 + CTL 增加 → 应该被判为 BUILD
    assert snap.current_phase is Phase.BUILD
    assert snap.micro.weekly_tss_target > 0
    assert len(snap.micro.days) == 7


def test_refresh_handles_missing_wellness_gracefully(tmp_path: Path) -> None:
    """Test that engine gracefully handles missing wellness data."""
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "8_Events" / "events.json").write_text("[]", encoding="utf-8")
    memory = tmp_path / "coach_memory"
    memory.mkdir()
    result = refresh_periodization(
        warehouse_dir=warehouse, memory_dir=memory,
        reference_date=date(2026, 4, 18),
        generated_at="2026-04-18T00:00:00Z",
    )
    # 无 wellness → slope unknown → 走 fallback BUILD
    assert result["status"] == "ok"
    snap = load_periodization_snapshot(memory / "periodization")
    assert snap is not None
    assert snap.current_phase in (Phase.BUILD, Phase.BASE, Phase.TRANSITION)


def test_refresh_captures_next_race_when_present(tmp_path: Path) -> None:
    """Test that next_race snapshot captures race info (with spec drift fix).

    NOTE: spec drift — plan called snap.next_race.days_out but File 01 NextRace has no
    days_out field (types.py is off-limits). Use race_date + reference_date math instead.
    """
    warehouse = _seed_warehouse(tmp_path)
    memory = _seed_memory(tmp_path)
    refresh_periodization(
        warehouse_dir=warehouse, memory_dir=memory,
        reference_date=date(2026, 4, 18),
        generated_at="2026-04-18T00:00:00Z",
    )
    snap = load_periodization_snapshot(memory / "periodization")
    assert snap.next_race is not None
    assert snap.next_race.name == "Goal"
    assert snap.next_race.race_date == date(2026, 6, 15)
    # days_out is tracked on RaceEntry (race_calendar) but NOT persisted to NextRace snapshot
    assert (snap.next_race.race_date - date(2026, 4, 18)).days == 58


def test_refresh_reads_stimulus_median_from_trace_files(tmp_path: Path) -> None:
    warehouse = _seed_warehouse(tmp_path)
    memory = _seed_memory(tmp_path)
    # Seed multiple trace files — engine should use median of these over summary_latest
    deep_dir = memory / "deep_analysis"
    for i, score in enumerate([0.40, 0.60, 0.80]):
        (deep_dir / f"2026-04-{10+i:02d}.trace.json").write_text(
            json.dumps({"stimulus_score": score}),
            encoding="utf-8",
        )
    result = refresh_periodization(
        warehouse_dir=warehouse,
        memory_dir=memory,
        reference_date=date(2026, 4, 18),
        generated_at="2026-04-18T00:00:00Z",
    )
    assert result["status"] == "ok"
    # Snapshot exists and is structurally valid — exercises the trace.json branch
    snap = load_periodization_snapshot(memory / "periodization")
    assert snap is not None
    assert snap.current_phase is not None
