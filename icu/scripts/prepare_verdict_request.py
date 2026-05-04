"""Build a verdict_request.json from current coach_memory + warehouse state.

Usage:
    .venv/bin/python scripts/prepare_verdict_request.py \\
        [--memory coach_memory] [--warehouse icu_data_warehouse] \\
        [--date YYYY-MM-DD] [--wellness-trend-days 7] \\
        [--out /tmp/verdict_request.json]

Defaults pull from local conventions; output goes to ./verdict_request.json
unless --out provided.

Exit codes:
    0  success (output written, path printed)
    1  fixture/data missing (no plan, no wellness, etc.)
    2  CLI argument error
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.coach.common.verdict_request_builder import (  # noqa: E402
    build_verdict_request_payload,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--memory", type=Path, default=Path("coach_memory"),
                   help="coach_memory dir (default: coach_memory)")
    p.add_argument("--warehouse", type=Path, default=Path("icu_data_warehouse"),
                   help="warehouse dir (default: icu_data_warehouse)")
    p.add_argument("--date", type=str, default=None,
                   help="target date YYYY-MM-DD (default: today UTC)")
    p.add_argument("--wellness-trend-days", type=int, default=7,
                   help="how many recent wellness entries to include (default 7)")
    p.add_argument("--out", type=Path, default=Path("verdict_request.json"),
                   help="output JSON path (default: ./verdict_request.json)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    target_date = (date.fromisoformat(args.date) if args.date
                   else datetime.utcnow().date())
    try:
        payload = build_verdict_request_payload(
            memory_dir=args.memory, warehouse_dir=args.warehouse,
            target_date=target_date,
            wellness_trend_days=args.wellness_trend_days,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2,
                                   sort_keys=True, ensure_ascii=False),
                        encoding="utf-8")
    print(f"Wrote verdict_request -> {args.out}")
    print(f"  plan.week_start = {payload['plan'].get('week_start')}")
    print(f"  athlete_state   = ctl={payload['athlete_state']['ctl']:.1f}  "
          f"atl={payload['athlete_state']['atl']:.1f}  "
          f"tsb={payload['athlete_state']['tsb']:+.1f}  "
          f"phase={payload['athlete_state']['phase']}")
    print(f"  wellness_trend  = {len(payload['wellness_trend'])} entries")
    print(f"\nNext: scripts/run_consensus.py --mode council "
          f"--verdict-request {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
