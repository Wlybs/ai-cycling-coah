"""CLI tests for scripts/ingest_ledger.py — subprocess round-trip of the wrapper.

Exercises the argparse layer + end-to-end wiring (script → LedgerIngester →
LedgerWriter file output). The Ingester unit logic is covered by
test_ingester.py; this file only validates the shell-facing surface.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# icu/tests/unit/ledger/test_ingest_ledger_cli.py → parents[3] = icu/
_ICU_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ICU_ROOT / "scripts" / "ingest_ledger.py"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_ICU_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _make_phase2_tree(tmp_path: Path) -> tuple[Path, Path]:
    memory = tmp_path / "coach_memory"
    warehouse = tmp_path / "icu_data_warehouse"
    (memory / "periodization").mkdir(parents=True)
    (memory / "ledger").mkdir(parents=True)
    (warehouse / "2_Wellness").mkdir(parents=True)
    return memory, warehouse


def test_script_exists():
    assert _SCRIPT.exists(), f"Expected {_SCRIPT} to exist"


def test_cli_help_exits_zero():
    cp = _run(["--help"], cwd=_ICU_ROOT)
    assert cp.returncode == 0, cp.stderr
    combined = (cp.stdout + cp.stderr).lower()
    assert "--memory" in combined
    assert "--warehouse" in combined


def test_cli_missing_required_flag_exits_nonzero(tmp_path):
    cp = _run([], cwd=tmp_path)
    assert cp.returncode != 0
    assert "required" in (cp.stderr + cp.stdout).lower() or "memory" in (cp.stderr + cp.stdout).lower()


def test_cli_writes_ledger_on_real_run(tmp_path):
    memory, warehouse = _make_phase2_tree(tmp_path)
    (memory / "periodization" / "phase_current.json").write_text(
        json.dumps({
            "current_phase": "BUILD",
            "reasons": ["ctl_slope_above_threshold"],
            "generated_at": "2026-04-26T10:00:00+00:00",
        }),
        encoding="utf-8",
    )

    cp = _run(["--memory", str(memory), "--warehouse", str(warehouse)], cwd=tmp_path)
    assert cp.returncode == 0, cp.stderr

    # Per-decision_type counts on stdout, e.g. "phase_transition: 1"
    assert "phase_transition: 1" in cp.stdout

    ledger = memory / "ledger" / "decisions.jsonl"
    assert ledger.exists()
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["decision_type"] == "phase_transition"
    assert entry["payload"]["to_phase"] == "BUILD"
    assert entry["payload"]["from_phase"] is None


def test_cli_is_idempotent_across_runs(tmp_path):
    memory, warehouse = _make_phase2_tree(tmp_path)
    (memory / "periodization" / "phase_current.json").write_text(
        json.dumps({"current_phase": "BUILD", "reasons": ["x"],
                    "generated_at": "2026-04-26T10:00:00+00:00"}),
        encoding="utf-8",
    )

    cp1 = _run(["--memory", str(memory), "--warehouse", str(warehouse)], cwd=tmp_path)
    assert cp1.returncode == 0, cp1.stderr
    assert "phase_transition: 1" in cp1.stdout

    cp2 = _run(["--memory", str(memory), "--warehouse", str(warehouse)], cwd=tmp_path)
    assert cp2.returncode == 0, cp2.stderr
    assert "phase_transition: 0" in cp2.stdout

    lines = (memory / "ledger" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


def test_cli_respects_ledger_override_flag(tmp_path):
    memory, warehouse = _make_phase2_tree(tmp_path)
    (memory / "periodization" / "phase_current.json").write_text(
        json.dumps({"current_phase": "BUILD", "reasons": ["x"],
                    "generated_at": "2026-04-26T10:00:00+00:00"}),
        encoding="utf-8",
    )
    custom_ledger = tmp_path / "custom_ledger.jsonl"

    cp = _run(
        ["--memory", str(memory), "--warehouse", str(warehouse),
         "--ledger", str(custom_ledger)],
        cwd=tmp_path,
    )
    assert cp.returncode == 0, cp.stderr
    assert custom_ledger.exists()
    assert not (memory / "ledger" / "decisions.jsonl").exists()
    lines = custom_ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["decision_type"] == "phase_transition"
