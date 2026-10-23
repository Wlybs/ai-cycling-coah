"""
Memory management utility for the Gemini coach system.
Cleans up expired entries in coach_memory/ files.

Usage:
    python scripts/manage_memory.py          # preview what would be cleaned
    python scripts/manage_memory.py --apply  # apply cleanup
    python scripts/manage_memory.py --status # show memory file summary
"""

import re
import shutil
import sys
import os
from datetime import date, datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path(__file__).parent.parent / "coach_memory"
ARCHIVE_DIR = MEMORY_DIR / "_archive"
TODAY = date.today()
PLAN_ARCHIVE_DAYS = 14


def parse_dated_sections(content: str) -> list[dict]:
    """Extract ## YYYY-MM-DD sections from a markdown file."""
    pattern = re.compile(r'^## (\d{4}-\d{2}-\d{2})[^\n]*', re.MULTILINE)
    matches = list(pattern.finditer(content))
    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        try:
            entry_date = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        sections.append({
            "date": entry_date,
            "header_line": m.group(0),
            "full_text": content[start:end],
            "start": start,
            "end": end,
        })
    return sections


# ── Body Status ────────────────────────────────────────────────────────────────

def clean_body_status(apply: bool = False) -> list[str]:
    """Remove [resolved] entries older than 30 days."""
    path = MEMORY_DIR / "body_status.md"
    content = path.read_text(encoding="utf-8")
    sections = parse_dated_sections(content)

    cutoff = TODAY - timedelta(days=30)
    removed = []
    new_content = content

    for s in reversed(sections):
        is_resolved = "[resolved]" in s["full_text"].lower()
        if is_resolved and s["date"] < cutoff:
            removed.append(f"  - {s['date']}: (resolved, > 30 days old)")
            if apply:
                new_content = new_content[: s["start"]] + new_content[s["end"] :]

    if apply and removed:
        path.write_text(new_content, encoding="utf-8")

    return removed


# ── Race Calendar ──────────────────────────────────────────────────────────────

def clean_race_calendar(apply: bool = False) -> list[str]:
    """Remove races more than 7 days in the past; log completions to coach_log."""
    path = MEMORY_DIR / "race_calendar.md"
    content = path.read_text(encoding="utf-8")
    sections = parse_dated_sections(content)

    cutoff = TODAY - timedelta(days=7)
    removed = []
    completions = []
    new_content = content

    for s in reversed(sections):
        if s["date"] < cutoff:
            race_name = s["header_line"].split("|")[1].strip() if "|" in s["header_line"] else "Unknown Race"
            removed.append(f"  - {s['date']}: {race_name}")
            completions.append(f"## {TODAY.isoformat()}: [Race completed] {s['date']} — {race_name}")
            if apply:
                new_content = new_content[: s["start"]] + new_content[s["end"] :]

    if apply and removed:
        path.write_text(new_content, encoding="utf-8")
        _append_to_coach_log(completions)

    return removed


# ── Coach Log ─────────────────────────────────────────────────────────────────

def clean_coach_log(apply: bool = False) -> list[str]:
    """Consolidate oldest 30 entries when log exceeds 80 entries."""
    path = MEMORY_DIR / "coach_log.md"
    content = path.read_text(encoding="utf-8")
    sections = parse_dated_sections(content)

    if len(sections) <= 80:
        return []

    oldest_30 = sections[:30]
    oldest_cutoff = oldest_30[-1]["date"]
    summary_lines = [f"## Summary (before {oldest_cutoff.isoformat()})"]
    for s in oldest_30:
        first_body_line = s["full_text"].split("\n", 2)[2].strip().split("\n")[0]
        summary_lines.append(f"- {s['date']}: {first_body_line}")
    summary_block = "\n".join(summary_lines) + "\n\n"

    log_entries_marker = "## Log Entries"
    if log_entries_marker in content:
        header_end = content.index(log_entries_marker) + len(log_entries_marker) + 1
        header = content[:header_end]
        # Find where first dated section starts
        first_section_start = oldest_30[0]["start"]
        last_to_remove_end = oldest_30[-1]["end"]
        remaining = content[last_to_remove_end:]
        new_content = header + "\n\n" + summary_block + remaining
    else:
        new_content = content

    msgs = [f"  Consolidated {len(oldest_30)} oldest entries into summary block (before {oldest_cutoff})"]
    if apply:
        path.write_text(new_content, encoding="utf-8")

    return msgs


def _append_to_coach_log(lines: list[str]) -> None:
    path = MEMORY_DIR / "coach_log.md"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


# ── Plan File Archiving ────────────────────────────────────────────────────────

_PLAN_DATE_PATTERNS = [
    re.compile(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})'),   # 20260328 / 2026-03-28 / 2026_03_28
    re.compile(r'(\d{1,2})[.\-_](\d{1,2})'),           # 0328 / 3.28 / 4_01
]


def _extract_plan_date(name: str) -> date | None:
    """Guess the anchor date from a filename like training_plan_0401_0403.md or
    training_plan_race_0328.md. Returns the LATEST date encoded, if multiple."""
    candidates = []
    for m in re.finditer(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', name):
        try:
            candidates.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue
    for m in re.finditer(r'[_-](\d{2})(\d{2})(?!\d)', name):
        mo, d = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                candidates.append(date(TODAY.year, mo, d))
            except ValueError:
                continue
    if not candidates:
        return None
    return max(candidates)


def _archive_file(path: Path, apply: bool, reason: str) -> str:
    dest = ARCHIVE_DIR / path.name
    if apply:
        ARCHIVE_DIR.mkdir(exist_ok=True)
        # Avoid overwriting older archive with same name
        if dest.exists():
            stem, ext = dest.stem, dest.suffix
            dest = ARCHIVE_DIR / f"{stem}_{TODAY.isoformat()}{ext}"
        shutil.move(str(path), str(dest))
    return f"  - {path.name} → _archive/{dest.name} ({reason})"


def clean_stale_plans(apply: bool = False) -> list[str]:
    """Archive training_plan_*.md / active_plan*.md files whose date anchor is older than PLAN_ARCHIVE_DAYS."""
    patterns = ["training_plan_*.md", "active_plan*.md", "plan_*.md"]
    cutoff = TODAY - timedelta(days=PLAN_ARCHIVE_DAYS)
    removed = []
    for pattern in patterns:
        for p in MEMORY_DIR.glob(pattern):
            plan_date = _extract_plan_date(p.stem)
            if plan_date and plan_date < cutoff:
                removed.append(_archive_file(p, apply, f"anchor date {plan_date}, >{PLAN_ARCHIVE_DAYS}d past"))
            elif plan_date is None:
                # No date found — fall back to mtime
                mtime_date = date.fromtimestamp(p.stat().st_mtime)
                if mtime_date < cutoff:
                    removed.append(_archive_file(p, apply, f"mtime {mtime_date}, >{PLAN_ARCHIVE_DAYS}d past"))
    return removed


# ── Status Overview ────────────────────────────────────────────────────────────

def show_status() -> None:
    files = [
        "athlete_snapshot.json",
        "fitness_trend.json",
        "training_history.json",
        "training_analysis.json",
        "plan_adherence.json",
        "body_status.md",
        "race_calendar.md",
        "nutrition_strategy.md",
        "coach_log.md",
        "periodization_2026.md",
        "pb_reference.md",
        "workout_library.md",
    ]
    print(f"\n{'File':<30} {'Size':>8}  {'Modified'}")
    print("-" * 60)
    for fname in files:
        p = MEMORY_DIR / fname
        if p.exists():
            stat = p.stat()
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{fname:<30} {size:>7}B  {mtime}")
        else:
            print(f"{fname:<30}   MISSING")

    # Race calendar summary
    rc = MEMORY_DIR / "race_calendar.md"
    if rc.exists():
        sections = parse_dated_sections(rc.read_text(encoding="utf-8"))
        upcoming = [s for s in sections if s["date"] >= TODAY]
        print(f"\nUpcoming races: {len(upcoming)}")
        for s in upcoming:
            name = s["header_line"].split("|")[1].strip() if "|" in s["header_line"] else "?"
            days_away = (s["date"] - TODAY).days
            print(f"  {s['date']}  {name}  ({days_away}d away)")

    # Body status summary
    bs = MEMORY_DIR / "body_status.md"
    if bs.exists():
        sections = parse_dated_sections(bs.read_text(encoding="utf-8"))
        active = [s for s in sections if "[active]" in s["full_text"].lower()]
        print(f"\nActive body issues: {len(active)}")
        for s in active:
            print(f"  {s['date']}: {s['header_line'].split(':', 1)[-1].strip()}")

    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    apply = "--apply" in sys.argv
    status_only = "--status" in sys.argv

    if status_only:
        show_status()
        return

    mode = "APPLY" if apply else "DRY RUN (use --apply to make changes)"
    print(f"\n=== Memory Cleanup — {mode} ===\n")

    print("Body Status (removing resolved entries > 30 days old):")
    removed = clean_body_status(apply)
    print("\n".join(removed) if removed else "  Nothing to remove.")

    print("\nRace Calendar (removing races > 7 days past):")
    removed = clean_race_calendar(apply)
    print("\n".join(removed) if removed else "  Nothing to remove.")

    print("\nCoach Log (consolidating if > 80 entries):")
    msgs = clean_coach_log(apply)
    print("\n".join(msgs) if msgs else "  Under limit, no consolidation needed.")

    print("\nStale Plan Files (archiving if anchor > 14 days past):")
    removed = clean_stale_plans(apply)
    print("\n".join(removed) if removed else "  None stale.")

    print()
    show_status()


if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    main()
