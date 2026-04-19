"""赛历加载。优先读 8_Events/events.json（RACE 分类或关键词），
回退到 coach_memory/race_calendar.md 简单行格式。"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

_logger = logging.getLogger(__name__)

RACE_KEYWORDS = ("race", "比赛", "爬坡赛", "赛", "climb")


class RaceEntry(BaseModel):
    name: str
    race_date: date
    priority: Literal["A", "B", "C"] = "A"
    course_hint: Optional[str] = None
    days_out: Optional[int] = None

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, v):
        """Map unknown/numeric/None priority values to 'C' (low-priority default)."""
        if v is None:
            return "A"
        s = str(v).strip().upper()
        if s in ("A", "B", "C"):
            return s
        return "C"


def _parse_event_date(raw: str) -> Optional[date]:
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _is_race(ev: dict) -> bool:
    cat = str(ev.get("category") or "").upper()
    if cat == "RACE":
        return True
    name = str(ev.get("name") or "").lower()
    return any(kw in name for kw in RACE_KEYWORDS)


_MD_LINE = re.compile(
    r"-\s*(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<pri>[ABC])\s+(?P<name>.+?)\s*$",
    re.IGNORECASE,
)


def _load_from_events(warehouse_dir: Path) -> list[RaceEntry]:
    path = Path(warehouse_dir) / "8_Events" / "events.json"
    if not path.exists():
        return []
    try:
        events = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _logger.warning("race_calendar: failed to parse %s: %s", path, e)
        return []
    out: list[RaceEntry] = []
    for ev in events:
        if not _is_race(ev):
            continue
        d = _parse_event_date(str(ev.get("start_date_local", "")))
        if not d:
            continue
        out.append(RaceEntry(
            name=ev.get("name") or "Race",
            race_date=d,
            priority=ev.get("priority", "A"),
            course_hint=ev.get("description"),
        ))
    return out


def _load_from_markdown(memory_dir: Path) -> list[RaceEntry]:
    path = Path(memory_dir) / "race_calendar.md"
    if not path.exists():
        return []
    out: list[RaceEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _MD_LINE.match(line.strip())
        if not m:
            continue
        try:
            d = datetime.strptime(m.group("date"), "%Y-%m-%d").date()
        except ValueError:
            continue
        out.append(RaceEntry(
            name=m.group("name").strip(),
            race_date=d,
            priority=m.group("pri").upper(),
        ))
    return out


def _dedup_sorted(entries: list[RaceEntry]) -> list[RaceEntry]:
    seen: dict[tuple[str, date], RaceEntry] = {}
    for e in entries:
        key = (e.name.strip().lower(), e.race_date)
        seen.setdefault(key, e)
    return sorted(seen.values(), key=lambda e: e.race_date)


def load_race_calendar(
    warehouse_dir: Path, memory_dir: Path
) -> list[RaceEntry]:
    primary = _load_from_events(warehouse_dir)
    if primary:
        return _dedup_sorted(primary)
    return _dedup_sorted(_load_from_markdown(memory_dir))


def next_race_after(
    races: list[RaceEntry], reference_date: date
) -> Optional[RaceEntry]:
    future = [r for r in races if r.race_date >= reference_date]
    if not future:
        return None
    nxt = sorted(future, key=lambda r: r.race_date)[0]
    nxt = nxt.model_copy(update={"days_out": (nxt.race_date - reference_date).days})
    return nxt
