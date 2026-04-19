from datetime import date
from pathlib import Path

from src.coach.periodization.race_calendar import (
    RaceEntry, load_race_calendar, next_race_after,
)


def test_load_events_filters_race_category(tmp_path):
    events = [
        {"id": 1, "category": "RACE", "name": "Hill Climb 5.26",
         "start_date_local": "2026-05-26T08:00:00"},
        {"id": 2, "category": "WORKOUT", "name": "Endurance",
         "start_date_local": "2026-04-20T09:00:00"},
    ]
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "8_Events" / "events.json").write_text(
        __import__("json").dumps(events, ensure_ascii=False))
    races = load_race_calendar(warehouse_dir=warehouse, memory_dir=tmp_path)
    assert len(races) == 1
    assert races[0].name.startswith("Hill Climb")


def test_keyword_fallback_when_category_missing(tmp_path):
    events = [
        {"id": 99, "name": "Spring 爬坡赛",
         "start_date_local": "2026-05-10T08:00:00"},
    ]
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "8_Events" / "events.json").write_text(
        __import__("json").dumps(events, ensure_ascii=False))
    races = load_race_calendar(warehouse_dir=warehouse, memory_dir=tmp_path)
    assert len(races) == 1
    assert "爬坡" in races[0].name


def test_markdown_fallback_when_events_missing(tmp_path):
    memory = tmp_path / "coach_memory"
    memory.mkdir()
    (memory / "race_calendar.md").write_text(
        "- 2026-06-15 A 武夷山爬坡赛\n- 2026-07-20 B 环太湖\n",
        encoding="utf-8",
    )
    races = load_race_calendar(warehouse_dir=tmp_path, memory_dir=memory)
    assert len(races) == 2
    assert races[0].priority == "A"
    assert races[1].name.startswith("环太湖")


def test_next_race_after_reference_date():
    races = [
        RaceEntry(name="Past", race_date=date(2026, 3, 1), priority="B"),
        RaceEntry(name="Goal", race_date=date(2026, 5, 26), priority="A"),
        RaceEntry(name="Later", race_date=date(2026, 7, 20), priority="B"),
    ]
    nxt = next_race_after(races, reference_date=date(2026, 4, 18))
    assert nxt.name == "Goal"
    assert nxt.days_out == (date(2026, 5, 26) - date(2026, 4, 18)).days
