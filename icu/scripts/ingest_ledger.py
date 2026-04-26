"""Phase 3 — back-fill the decision ledger from Phase 2 artefacts.

Reads:
  --memory     coach_memory/   directory (periodization/* + reports/* + physiology/*)
  --warehouse  icu_data_warehouse/ directory (2_Wellness/wellness_history.json)
  --ledger     coach_memory/ledger/decisions.jsonl (default if --memory given)

Writes one entry per **new** Phase 2 artefact into the ledger (idempotent).
Prints the count of new entries per decision_type to stdout.

Exit code:
  0 — success (even when nothing new found)
  1 — fatal error (Pydantic schema mismatch, IO error)

API-free: imports nothing from google.genai or any LLM SDK.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

# Allow `python scripts/ingest_ledger.py ...` from icu/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.ledger.ingester import LedgerIngester  # noqa: E402
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.types import AthleteStateRef  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402


# Conservative fallback when warehouse / physiology snapshots are absent.
# Picked to be uninformative for query_similar (so unseeded entries don't
# pollute "similar context" hits with phantom CTL=0 matches).
_FALLBACK_STATE = AthleteStateRef(
    ctl=0.0, atl=0.0, tsb=0.0, w_prime=0,
    phase="UNKNOWN", week_of_year=date.today().isocalendar()[1],
)


def _read_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_default_state(memory_dir: Path, warehouse_dir: Path) -> AthleteStateRef:
    """Best-effort AthleteStateRef from current snapshots.

    Falls back to _FALLBACK_STATE if any required source is missing/malformed.
    """
    wellness = _read_json(warehouse_dir / "2_Wellness" / "wellness_history.json")
    cp_w = _read_json(memory_dir / "physiology" / "cp_w_current.json")
    phase_doc = _read_json(memory_dir / "periodization" / "phase_current.json")

    if not isinstance(wellness, list) or not wellness:
        return _FALLBACK_STATE
    latest = wellness[-1]
    ctl = latest.get("ctl")
    atl = latest.get("atl")
    if ctl is None or atl is None:
        return _FALLBACK_STATE

    w_prime = (cp_w or {}).get("w_prime_joules", 0)
    phase = (phase_doc or {}).get("current_phase", "UNKNOWN")

    try:
        return AthleteStateRef(
            ctl=float(ctl),
            atl=float(atl),
            tsb=float(ctl) - float(atl),
            w_prime=int(w_prime),
            phase=str(phase),
            week_of_year=date.today().isocalendar()[1],
        )
    except Exception:
        return _FALLBACK_STATE


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Back-fill the Phase 3 decision ledger from Phase 2 artefacts.",
    )
    p.add_argument("--memory", required=True, type=Path, help="coach_memory/ directory")
    p.add_argument("--warehouse", required=True, type=Path, help="icu_data_warehouse/ directory")
    p.add_argument("--ledger", type=Path, default=None,
                   help="ledger JSONL path (default: <memory>/ledger/decisions.jsonl)")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    memory: Path = args.memory
    warehouse: Path = args.warehouse
    ledger_path: Path = args.ledger or (memory / "ledger" / "decisions.jsonl")

    state = build_default_state(memory, warehouse)
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)
    ingester = LedgerIngester(
        memory_dir=memory,
        ledger_writer=writer,
        ledger_reader=reader,
        default_state=state,
    )
    counts = ingester.ingest_all()
    for k, v in counts.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
