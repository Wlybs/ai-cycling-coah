"""Phase 3 — Daily adaptation: 4-signal evaluation + (red) downgrade synthesis.

Reads:
  --memory     coach_memory/
  --warehouse  icu_data_warehouse/
  --date       YYYY-MM-DD
  [--ledger    coach_memory/ledger/decisions.jsonl] (default if --memory given)
  [--dry-run]  skip ALL writes (markdown / proposed_session / ledger)

Always-on side effects (when not --dry-run):
  - coach_memory/adapter/today_<date>.md    (yellow / red only)
  - coach_memory/adapter/proposed_session_<date>.json  (red + non-Rest only)
  - coach_memory/ledger/decisions.jsonl     (one append per call)

Never touches the network. apply_adaptation.py is the human-gate that pushes to ICU.

Exit codes:
  0 — success (any verdict, including dry-run)
  1 — fatal (wellness missing, schema mismatch, IO error)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

# Allow `python scripts/daily_adapt.py ...` from icu/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.adapter.daily_adapt import run  # noqa: E402
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Phase 3 daily adaptation — evaluate signals, "
            "optionally write outputs."
        ),
    )
    p.add_argument("--date", required=True, type=date.fromisoformat,
                   help="Target date YYYY-MM-DD")
    p.add_argument("--memory", required=True, type=Path,
                   help="coach_memory/ directory")
    p.add_argument("--warehouse", required=True, type=Path,
                   help="icu_data_warehouse/ directory")
    p.add_argument("--ledger", type=Path, default=None,
                   help="ledger JSONL path (default: <memory>/ledger/decisions.jsonl)")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip ALL writes (markdown / proposed_session / ledger)")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    ledger_path = args.ledger or (args.memory / "ledger" / "decisions.jsonl")
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    try:
        result = run(
            target_date=args.date,
            memory_dir=args.memory,
            warehouse_dir=args.warehouse,
            writer=writer, reader=reader,
            now_fn=lambda: datetime.now(timezone.utc),
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out = {
        k: (str(v) if isinstance(v, Path) else v)
        for k, v in result.items()
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
