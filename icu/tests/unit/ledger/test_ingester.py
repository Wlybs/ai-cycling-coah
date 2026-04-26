"""Unit tests for LedgerIngester: scan Phase 2 artifacts and back-fill ledger entries."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.coach.ledger.ingester import LedgerIngester
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter


# ---------- helpers to fabricate minimal Phase 2 artefacts ----------

def _write_phase_current(memory_dir: Path, phase: str, generated_at: str = "2026-04-19T00:00:00Z"):
    p = memory_dir / "periodization"
    p.mkdir(parents=True, exist_ok=True)
    (p / "phase_current.json").write_text(json.dumps({
        "generated_at": generated_at,
        "current_phase": phase,
        "reasons": [f"snapshot at {generated_at}"],
    }), encoding="utf-8")


def _write_macro_plan(memory_dir: Path, generated_at: str, season_end="2026-09-30",
                      phase_sequence=("BASE", "BUILD", "PEAK")):
    p = memory_dir / "periodization"
    p.mkdir(parents=True, exist_ok=True)
    windows = []
    for i, ph in enumerate(phase_sequence):
        windows.append({
            "phase": ph,
            "start_date": f"2026-0{i+4}-01",
            "end_date": f"2026-0{i+4}-28",
            "intent": {
                "phase": ph,
                "primary_adaptation": "x",
                "weekly_tss_target": 500,
                "intensity_distribution_pct": {"low": 75, "mid": 15, "high": 10},
                "rest_days_per_week": 1,
                "rationale": "test",
            },
        })
    (p / "macro_plan.json").write_text(json.dumps({
        "generated_at": generated_at,
        "season_end_date": season_end,
        "windows": windows,
    }), encoding="utf-8")


def _write_meso_block(memory_dir: Path, block_start="2026-04-06", block_end="2026-04-26",
                      pattern="3:1", phase="BUILD"):
    p = memory_dir / "periodization"
    p.mkdir(parents=True, exist_ok=True)
    (p / "meso_block.json").write_text(json.dumps({
        "pattern": pattern,
        "block_start": block_start,
        "block_end": block_end,
        "weekly_load_multipliers": [1.0, 1.05, 1.1, 0.7],
        "phase": phase,
    }), encoding="utf-8")


def _write_micro_cycle(memory_dir: Path, iso_year: int, iso_week: int,
                       week_start="2026-04-20", phase="BUILD"):
    p = memory_dir / "periodization"
    p.mkdir(parents=True, exist_ok=True)
    days = [{"day_of_week": d, "tier": "EASY", "target_tss": 40, "session_hint": "x"}
            for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
    days[1]["tier"] = "HARD"
    days[5]["tier"] = "HARD"
    (p / f"micro_cycle_{iso_year}-W{iso_week:02d}.json").write_text(json.dumps({
        "week_start": week_start,
        "week_end": "2026-04-26",
        "phase": phase,
        "intent": {
            "phase": phase, "primary_adaptation": "x", "weekly_tss_target": 450,
            "intensity_distribution_pct": {"low": 75, "mid": 15, "high": 10},
            "rest_days_per_week": 1, "rationale": "test",
        },
        "days": days,
        "weekly_tss_target": 450,
    }), encoding="utf-8")


def _write_weekly_plan(memory_dir: Path, week_start="2026-04-20", total_tss=480):
    p = memory_dir / "reports"
    p.mkdir(parents=True, exist_ok=True)
    tag = week_start.replace("-", "")
    (p / f"plan_{tag}.json").write_text(json.dumps({
        "week_start": week_start,
        "week_end": "2026-04-26",
        "focus_theme": "build threshold",
        "weekly_tss_target": total_tss,
        "coaching_summary": None,
        "days": [],
    }), encoding="utf-8")
    (p / f"plan_{tag}.trace.json").write_text(json.dumps({
        "composer_version": "v2",
        "physiology_snapshot_ref": "cp_w_current.json",
        "sessions": [{"date": week_start, "source_template": "z2_long"}],
    }), encoding="utf-8")


@pytest.fixture
def ingester(tmp_path, sample_state) -> LedgerIngester:
    ledger = tmp_path / "decisions.jsonl"
    return LedgerIngester(
        memory_dir=tmp_path,
        ledger_writer=LedgerWriter(ledger),
        ledger_reader=LedgerReader(ledger),
        default_state=sample_state,
    )


# ---------- phase_transition ----------

def test_phase_transition_first_write(tmp_path, ingester):
    _write_phase_current(tmp_path, "BUILD")
    n = ingester._ingest_phase_current()
    assert n == 1
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="phase_transition")
    assert len(entries) == 1
    assert entries[0].payload["to_phase"] == "BUILD"


def test_phase_transition_same_phase_no_new_entry(tmp_path, ingester):
    _write_phase_current(tmp_path, "BUILD")
    ingester._ingest_phase_current()
    # Re-run with same phase
    ingester._ingest_phase_current()
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="phase_transition")
    assert len(entries) == 1


def test_phase_transition_change_writes_new(tmp_path, ingester):
    _write_phase_current(tmp_path, "BUILD")
    ingester._ingest_phase_current()
    _write_phase_current(tmp_path, "PEAK", generated_at="2026-05-10T00:00:00Z")
    ingester._ingest_phase_current()
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="phase_transition")
    assert len(entries) == 2
    assert entries[-1].payload["from_phase"] == "BUILD"
    assert entries[-1].payload["to_phase"] == "PEAK"


# ---------- macro_plan_generated ----------

def test_macro_plan_first_write(tmp_path, ingester):
    _write_macro_plan(tmp_path, generated_at="2026-04-01T00:00:00Z")
    n = ingester._ingest_macro_plan()
    assert n == 1
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="macro_plan_generated")
    assert len(entries) == 1
    assert entries[0].payload["generated_at"] == "2026-04-01T00:00:00Z"
    assert entries[0].payload["windows_count"] == 3
    assert entries[0].payload["phase_sequence"] == ["BASE", "BUILD", "PEAK"]


def test_macro_plan_idempotent_on_same_generated_at(tmp_path, ingester):
    _write_macro_plan(tmp_path, generated_at="2026-04-01T00:00:00Z")
    ingester._ingest_macro_plan()
    ingester._ingest_macro_plan()  # second pass no-op
    assert len(LedgerReader(tmp_path / "decisions.jsonl").query(
        decision_type="macro_plan_generated")) == 1


# ---------- meso_block_created ----------

def test_meso_block_unique_by_block_start(tmp_path, ingester):
    _write_meso_block(tmp_path, block_start="2026-04-06")
    ingester._ingest_meso_block()
    ingester._ingest_meso_block()
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="meso_block_created")
    assert len(entries) == 1
    assert entries[0].payload["block_start"] == "2026-04-06"
    assert entries[0].payload["pattern"] == "3:1"


def test_meso_block_new_block_writes_new(tmp_path, ingester):
    _write_meso_block(tmp_path, block_start="2026-04-06")
    ingester._ingest_meso_block()
    _write_meso_block(tmp_path, block_start="2026-04-27", block_end="2026-05-17", phase="PEAK")
    ingester._ingest_meso_block()
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="meso_block_created")
    assert len(entries) == 2


# ---------- micro_cycle_generated ----------

def test_micro_cycle_collects_all_files(tmp_path, ingester):
    _write_micro_cycle(tmp_path, 2026, 16, week_start="2026-04-13")
    _write_micro_cycle(tmp_path, 2026, 17, week_start="2026-04-20")
    n = ingester._ingest_micro_cycles()
    assert n == 2
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="micro_cycle_generated")
    week_starts = {e.payload["week_start"] for e in entries}
    assert week_starts == {"2026-04-13", "2026-04-20"}


def test_micro_cycle_idempotent(tmp_path, ingester):
    _write_micro_cycle(tmp_path, 2026, 16, week_start="2026-04-13")
    ingester._ingest_micro_cycles()
    ingester._ingest_micro_cycles()
    assert len(LedgerReader(tmp_path / "decisions.jsonl").query(
        decision_type="micro_cycle_generated")) == 1


# ---------- weekly_plan_assembled ----------

def test_weekly_plan_with_trace_writes_entry(tmp_path, ingester):
    _write_weekly_plan(tmp_path, week_start="2026-04-20", total_tss=480)
    n = ingester._ingest_weekly_plans()
    assert n == 1
    entries = LedgerReader(tmp_path / "decisions.jsonl").query(decision_type="weekly_plan_assembled")
    assert len(entries) == 1
    assert entries[0].payload["plan_date"] == "2026-04-20"
    assert entries[0].payload["total_tss"] == 480


def test_weekly_plan_idempotent(tmp_path, ingester):
    _write_weekly_plan(tmp_path, week_start="2026-04-20")
    ingester._ingest_weekly_plans()
    ingester._ingest_weekly_plans()
    assert len(LedgerReader(tmp_path / "decisions.jsonl").query(
        decision_type="weekly_plan_assembled")) == 1


# ---------- ingest_all + missing files ----------

def test_ingest_all_returns_counts(tmp_path, ingester):
    _write_phase_current(tmp_path, "BUILD")
    _write_macro_plan(tmp_path, generated_at="2026-04-01T00:00:00Z")
    _write_meso_block(tmp_path)
    _write_micro_cycle(tmp_path, 2026, 16, week_start="2026-04-13")
    _write_weekly_plan(tmp_path, week_start="2026-04-20")
    counts = ingester.ingest_all()
    assert counts == {
        "phase_transition": 1,
        "macro_plan_generated": 1,
        "meso_block_created": 1,
        "micro_cycle_generated": 1,
        "weekly_plan_assembled": 1,
    }


def test_ingest_all_idempotent_on_second_run(tmp_path, ingester):
    _write_phase_current(tmp_path, "BUILD")
    _write_macro_plan(tmp_path, generated_at="2026-04-01T00:00:00Z")
    _write_meso_block(tmp_path)
    _write_micro_cycle(tmp_path, 2026, 16, week_start="2026-04-13")
    _write_weekly_plan(tmp_path, week_start="2026-04-20")
    ingester.ingest_all()
    counts = ingester.ingest_all()
    # Second run: nothing new
    assert all(v == 0 for v in counts.values())


def test_ingest_missing_files_returns_zero(tmp_path, ingester):
    counts = ingester.ingest_all()
    assert counts == {
        "phase_transition": 0,
        "macro_plan_generated": 0,
        "meso_block_created": 0,
        "micro_cycle_generated": 0,
        "weekly_plan_assembled": 0,
    }
