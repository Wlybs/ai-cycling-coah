"""Preview Phase 2 plan generation locally without Gemini or ICU push.

Usage:
  python scripts/plan_preview.py
  python scripts/plan_preview.py --week 2026-04-20
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from src.coach.session_designer.generator_v2 import generate_plan_v2
from src.utils.common import get_warehouse_dir


def _parse_week(raw: str | None) -> date:
    """Parse ISO date string or calculate next Monday.

    Args:
        raw: ISO date string (YYYY-MM-DD) or None

    Returns:
        Monday of the target week
    """
    if raw is None:
        today = datetime.now().date()
        # Calculate days until next Monday
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        return today + timedelta(days=days_until_monday)
    d = datetime.strptime(raw, "%Y-%m-%d").date()
    # Normalize to Monday of that week
    return d - timedelta(days=d.weekday())


def main(
    warehouse_dir: Path | None = None,
    memory_dir: Path | None = None,
    reports_dir: Path | None = None,
    week_start_iso: str | None = None,
) -> None:
    """Generate and preview a weekly plan.

    Args:
        warehouse_dir: Path to icu_data_warehouse
        memory_dir: Path to coach_memory
        reports_dir: Path to reports output
        week_start_iso: ISO date string (YYYY-MM-DD) for plan week (Monday)
    """
    warehouse_dir = warehouse_dir or Path(get_warehouse_dir())
    memory_dir = memory_dir or (warehouse_dir.parent / "coach_memory")
    reports_dir = reports_dir or (warehouse_dir.parent / "reports")

    # Parse week from argument or default to next Monday
    week_start = _parse_week(week_start_iso)
    week_end = week_start + timedelta(days=6)

    print(f"📝 Preview Phase 2 plan: {week_start} → {week_end}")
    result = generate_plan_v2(
        week_start=week_start,
        week_end=week_end,
        warehouse_dir=warehouse_dir,
        memory_dir=memory_dir,
        reports_dir=reports_dir,
        push_to_icu=False,
    )

    if result.status != "ok":
        print(f"❌ preview failed: {result.error}")
        return

    # Load and display plan
    plan = json.loads(Path(result.plan_json_path).read_text(encoding="utf-8"))
    print(f"\n=== WeeklyPlan ({plan['week_start']} → {plan['week_end']}) ===")
    print(f"Focus: {plan['focus_theme']}")
    print(f"TSS target: {plan['weekly_tss_target']}")
    print("\n| Day | Type        | Name                         | min | TSS | Power     |")
    print("|-----|-------------|------------------------------|-----|-----|-----------|")
    for d in plan["days"]:
        power = d.get("power_range_w") or d.get("hr_range_bpm") or "-"
        print(f"| {d['day_of_week']} | {d['training_type']:<11} | "
              f"{d['name'][:28]:<28} | {d['duration_min']:>3} | "
              f"{d['target_tss']:>3} | {power:<9} |")

    if result.violations:
        print("\n⚠️  未解决护栏：")
        for v in result.violations:
            print(f"  - {v['rule']}: {v['message']} → {v['suggested_action']}")

    print(f"\n📄 {result.plan_json_path}")
    print(f"📄 {result.plan_md_path}")
    print(f"📄 {result.trace_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preview Phase 2 weekly plan generation"
    )
    parser.add_argument(
        "--week",
        type=str,
        default=None,
        help="Target week start date (YYYY-MM-DD, defaults to next Monday)",
    )
    args = parser.parse_args()
    main(week_start_iso=args.week)
