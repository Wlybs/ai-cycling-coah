"""Phase 3 — Apply adapter's red-verdict downgrade to ICU (human-gated).

Default behavior: print the PUT payload that would be sent; exit 0.
With --confirm: actually call ICUClient.update_event; on success append
`adaptation_applied` to ledger; on failure leave ledger untouched and exit 2.

Reads:
  --memory     coach_memory/
  --warehouse  icu_data_warehouse/
  --date       YYYY-MM-DD
  [--confirm]  send the PUT to ICU
  [--ledger    coach_memory/ledger/decisions.jsonl]

Exit codes:
  0 — success (dry-run or applied)
  1 — pre-flight failure (no verdict, no event, malformed input)
  2 — PUT itself failed (network, HTTP error)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

# Allow `python scripts/apply_adaptation.py ...` from icu/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.adapter.apply_adaptation import run  # noqa: E402
from src.coach.ledger.reader import LedgerReader  # noqa: E402
from src.coach.ledger.writer import LedgerWriter  # noqa: E402
from src.fetcher.icu_client import ICUClient  # noqa: E402


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Phase 3 apply adaptation — push red-verdict downgrade to ICU "
            "(human-gated)."
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
    gate = p.add_mutually_exclusive_group()
    gate.add_argument("--confirm", action="store_true",
                      help="Actually send the PUT to ICU. Default = dry-run print only.")
    gate.add_argument("--dry-run", action="store_true",
                      help="Explicit dry-run (default behavior; mutually exclusive with --confirm).")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    ledger_path = args.ledger or (args.memory / "ledger" / "decisions.jsonl")
    writer = None if not args.confirm else LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)

    try:
        result = run(
            target_date=args.date,
            memory_dir=args.memory,
            warehouse_dir=args.warehouse,
            client_factory=lambda: ICUClient(),
            writer=writer, reader=reader,
            now_fn=lambda: datetime.now(timezone.utc),
            confirm=args.confirm,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # PUT failed
        print(f"PUT FAILED: {exc}", file=sys.stderr)
        return 2

    out = {
        k: (str(v) if isinstance(v, Path) else v)
        for k, v in result.items()
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    if not args.confirm:
        print(
            "\n[dry-run] no changes were sent. Re-run with --confirm to apply.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
