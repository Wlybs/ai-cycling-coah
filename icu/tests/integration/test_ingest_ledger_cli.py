"""Integration test for `scripts/ingest_ledger.py` CLI."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

from src.coach.ledger.reader import LedgerReader

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


def _seed_inputs(memory: Path, warehouse: Path):
    # periodization/phase_current.json
    (memory / "periodization").mkdir(parents=True, exist_ok=True)
    (memory / "periodization" / "phase_current.json").write_text(json.dumps({
        "generated_at": "2026-04-19T00:00:00Z",
        "current_phase": "BUILD",
        "reasons": ["test seed"],
    }))
    # physiology/cp_w_current.json
    (memory / "physiology").mkdir(parents=True, exist_ok=True)
    (memory / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 280, "w_prime_joules": 18500, "fit_r_squared": 0.95,
        "athlete_ftp_set": 288,
    }))
    # warehouse/2_Wellness/wellness_history.json
    wd = warehouse / "2_Wellness"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "wellness_history.json").write_text(json.dumps([
        {"id": "2026-04-18", "ctl": 72.3, "atl": 85.1},
        {"id": "2026-04-19", "ctl": 72.5, "atl": 85.8},
    ]))


def test_main_runs_and_writes_ledger_entries(tmp_path, monkeypatch, capsys):
    memory = tmp_path / "coach_memory"
    warehouse = tmp_path / "icu_data_warehouse"
    ledger_path = memory / "ledger" / "decisions.jsonl"
    _seed_inputs(memory, warehouse)

    import ingest_ledger as cli  # type: ignore[import]
    rc = cli.main([
        "--memory", str(memory),
        "--warehouse", str(warehouse),
        "--ledger", str(ledger_path),
    ])
    assert rc == 0

    entries = LedgerReader(ledger_path).query()
    assert len(entries) == 1   # only phase_current was seeded
    assert entries[0].decision_type == "phase_transition"
    assert entries[0].payload["to_phase"] == "BUILD"
    assert entries[0].athlete_state_ref.ctl == pytest.approx(72.5)

    out = capsys.readouterr().out
    assert "phase_transition: 1" in out


def test_main_with_missing_inputs_exits_zero_with_zeros(tmp_path, capsys):
    memory = tmp_path / "coach_memory"
    warehouse = tmp_path / "icu_data_warehouse"
    memory.mkdir()
    warehouse.mkdir()
    ledger_path = memory / "ledger" / "decisions.jsonl"

    import ingest_ledger as cli  # type: ignore[import]
    rc = cli.main([
        "--memory", str(memory),
        "--warehouse", str(warehouse),
        "--ledger", str(ledger_path),
    ])
    assert rc == 0

    out = capsys.readouterr().out
    assert "phase_transition: 0" in out
