"""Tests for workout_text → ZWO parsing and ICU event ids in plan_generator."""
import pytest

from src.coach.plan_generator import (
    _build_event_payload,
    _build_rest_payload,
    _parse_intensity,
    _workout_text_to_zwo,
)


def test_parse_intensity_accepts_percent_and_zone():
    assert _parse_intensity("150%") == pytest.approx(1.5)
    assert _parse_intensity("z2") == pytest.approx(0.65)


def test_parse_intensity_rejects_absolute_watts():
    with pytest.raises(ValueError):
        _parse_intensity("200W")


def test_repeat_block_without_on_off_lines_raises():
    with pytest.raises(ValueError):
        _workout_text_to_zwo("3x\n- 1m 150%")


def test_repeat_block_becomes_intervals():
    zwo = _workout_text_to_zwo("- 10m Z2\n3x\n- 1m 150%\n- 1m 50%\n- 10m Z2")
    assert '<IntervalsT Repeat="3" OnDuration="60" OffDuration="60"' in zwo
    assert "<Warmup Duration=\"600\"" in zwo
    assert "<Cooldown Duration=\"600\"" in zwo


def test_rest_and_workout_on_same_date_have_distinct_ids():
    day = {"name": "a", "date": "2026-10-24", "workout_text": "- 1h Z2"}
    workout = _build_event_payload(day)
    rest = _build_rest_payload({"date": "2026-10-24"})
    assert workout["external_id"] == "vault_plan_20261024"
    assert rest["external_id"] != workout["external_id"]


def test_second_workout_same_date_gets_suffix():
    day = {"name": "b", "date": "2026-10-24", "workout_text": "- 1h Z2"}
    assert _build_event_payload(day, slot=2)["external_id"] == "vault_plan_20261024_2"
