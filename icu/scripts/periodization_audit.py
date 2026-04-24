"""Print a human-readable summary of the current periodization snapshot.

Usage:
  python scripts/periodization_audit.py
  python scripts/periodization_audit.py --memory-dir <custom-path>
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from src.coach.periodization.snapshot_io import load_periodization_snapshot
from src.utils.common import get_warehouse_dir


def _fmt_date(d: date | str) -> str:
    """Format a date object or string."""
    if hasattr(d, "isoformat"):
        return d.isoformat()
    return str(d)


def main(memory_dir: Path | None = None) -> None:
    """Load and print periodization snapshot.

    Args:
        memory_dir: Path to coach_memory directory. Defaults to
                    get_warehouse_dir().parent / "coach_memory"
    """
    if memory_dir is None:
        memory_dir = Path(get_warehouse_dir()).parent / "coach_memory"
    memory_dir = Path(memory_dir)

    snap = load_periodization_snapshot(memory_dir / "periodization")
    if snap is None:
        print(f"❌ no snapshot found under {memory_dir / 'periodization'}")
        return

    print("=" * 64)
    print(f"Periodization Snapshot @ {snap.generated_at}")
    print(f"Current phase: {snap.current_phase.value}")
    if snap.next_race:
        print(f"Next race: {snap.next_race.name} on {_fmt_date(snap.next_race.race_date)} "
              f"(priority {snap.next_race.priority})")
    print("=" * 64)

    print("\nMacro plan:")
    print(f"  Season end: {_fmt_date(snap.macro.season_end_date)}")
    for w in snap.macro.windows:
        print(f"  [{w.phase.value:<10}] {_fmt_date(w.start_date)} → "
              f"{_fmt_date(w.end_date)}  "
              f"TSS target/wk={w.intent.weekly_tss_target}  "
              f"L/M/H={w.intent.intensity_distribution_pct}  "
              f"rest_days={w.intent.rest_days_per_week}")

    print("\nMeso block:")
    print(f"  pattern={snap.meso.pattern}  "
          f"{_fmt_date(snap.meso.block_start)} → "
          f"{_fmt_date(snap.meso.block_end)}")
    print(f"  load multipliers: {snap.meso.weekly_load_multipliers}")

    print("\nMicro cycle:")
    print(f"  {_fmt_date(snap.micro.week_start)} → "
          f"{_fmt_date(snap.micro.week_end)}  "
          f"TSS target={snap.micro.weekly_tss_target}")
    print(f"  rationale: {snap.micro.intent.rationale[:120]}")
    print("  " + "-" * 60)
    print(f"  {'Day':<4} {'Tier':<10} {'TSS':>5}  Hint")
    for d in snap.micro.days:
        print(f"  {d.day_of_week:<4} {d.tier.value:<10} "
              f"{d.target_tss:>5}  {d.session_hint}")
    print()


if __name__ == "__main__":
    main()
