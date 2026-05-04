"""Tests for src.coach.common.verdict_request_builder."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.coach.common.verdict_request_builder import build_verdict_request_payload
from src.coach.consensus.council_prompt import VerdictRequest


def _seed_corpus(tmp: Path, *, n_wellness: int = 7,
                 n_plans: int = 1, tsb_null: bool = False,
                 omit_plans: bool = False, omit_wellness: bool = False) -> tuple[Path, Path]:
    memory = tmp / "coach_memory"
    warehouse = tmp / "warehouse"
    (memory / "plans").mkdir(parents=True)
    (memory / "periodization").mkdir(parents=True)
    (memory / "physiology").mkdir(parents=True)
    (warehouse / "2_Wellness").mkdir(parents=True)

    if not omit_wellness:
        wellness = []
        for i in range(n_wellness):
            d = date(2026, 5, 4) - __import__("datetime").timedelta(days=n_wellness - 1 - i)
            wellness.append({
                "id": f"{d.isoformat()}T00:00:00",
                "ctl": 100.0 + i,
                "atl": 110.0 + i,
                "tsb": None if tsb_null else (100.0 + i) - (110.0 + i),
                "hrv": 60.0,
                "restingHR": 50,
                "sleepSecs": 25200,
                "soreness": None,
            })
        (warehouse / "2_Wellness" / "wellness_history.json").write_text(
            json.dumps(wellness), encoding="utf-8")

    if not omit_plans:
        for i in range(n_plans):
            d = date(2026, 5, 4) - __import__("datetime").timedelta(weeks=i)
            plan = {
                "week_start": d.isoformat(),
                "week_end": (d + __import__("datetime").timedelta(days=6)).isoformat(),
                "focus_theme": "BUILD",
                "weekly_tss_target": 525,
                "days": [{"day_of_week": "Mon", "training_type": "Endurance",
                          "name": "Z2 base", "duration_min": 90, "target_tss": 70,
                          "power_range_w": "150-180W", "tier": "MID"}],
            }
            (memory / "plans" / f"plan_{d.strftime('%Y%m%d')}.json").write_text(
                json.dumps(plan), encoding="utf-8")

    (memory / "periodization" / "phase_current.json").write_text(json.dumps({
        "current_phase": "BUILD", "generated_at": "2026-05-04T00:00:00Z",
    }), encoding="utf-8")
    (memory / "periodization" / "periodization_current.json").write_text(json.dumps({
        "current_phase": "BUILD", "weekly_tss_target": 525, "weeks_to_race": 8,
    }), encoding="utf-8")
    (memory / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 288, "w_prime_joules": 20000, "fit_r_squared": 0.95,
    }), encoding="utf-8")
    (memory / "physiology" / "durability.json").write_text(json.dumps({
        "decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1},
    }), encoding="utf-8")
    (memory / "physiology" / "response_profile.json").write_text(json.dumps({
        "types": {"vo2max": {"tolerance_class": "high"}},
    }), encoding="utf-8")
    return memory, warehouse


# ---------- Happy path ----------

def test_happy_path_returns_valid_verdict_request(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path)
    payload = build_verdict_request_payload(
        memory_dir=memory, warehouse_dir=warehouse,
        target_date=date(2026, 5, 4))
    # Validates against the real schema
    vr = VerdictRequest.model_validate(payload)
    assert vr.athlete_state.phase == "BUILD"
    assert vr.plan["focus_theme"] == "BUILD"


def test_athlete_state_pulled_from_latest_wellness(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path, n_wellness=5)
    payload = build_verdict_request_payload(
        memory_dir=memory, warehouse_dir=warehouse,
        target_date=date(2026, 5, 4))
    # Latest wellness has ctl = 100 + (5-1) = 104
    assert payload["athlete_state"]["ctl"] == 104.0
    assert payload["athlete_state"]["atl"] == 114.0


def test_tsb_computed_when_null(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path, n_wellness=3, tsb_null=True)
    payload = build_verdict_request_payload(
        memory_dir=memory, warehouse_dir=warehouse,
        target_date=date(2026, 5, 4))
    # tsb fallback = ctl - atl = 102 - 112 = -10
    assert payload["athlete_state"]["tsb"] == pytest.approx(-10.0)


def test_picks_latest_plan_when_multiple_present(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path, n_plans=3)
    payload = build_verdict_request_payload(
        memory_dir=memory, warehouse_dir=warehouse,
        target_date=date(2026, 5, 4))
    assert payload["plan"]["week_start"] == "2026-05-04"


def test_wellness_trend_respects_days_param(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path, n_wellness=14)
    payload = build_verdict_request_payload(
        memory_dir=memory, warehouse_dir=warehouse,
        target_date=date(2026, 5, 4),
        wellness_trend_days=5)
    assert len(payload["wellness_trend"]) == 5


def test_w_prime_pulled_from_cp_w_current(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path)
    payload = build_verdict_request_payload(
        memory_dir=memory, warehouse_dir=warehouse,
        target_date=date(2026, 5, 4))
    assert payload["athlete_state"]["w_prime"] == 20000


def test_week_of_year_derived_from_target_date(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path)
    payload = build_verdict_request_payload(
        memory_dir=memory, warehouse_dir=warehouse,
        target_date=date(2026, 5, 4))
    # 2026-05-04 is a Monday → ISO week 19
    assert payload["athlete_state"]["week_of_year"] == 19


def test_raises_when_no_plan(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path, omit_plans=True)
    with pytest.raises(FileNotFoundError, match="plan"):
        build_verdict_request_payload(
            memory_dir=memory, warehouse_dir=warehouse,
            target_date=date(2026, 5, 4))


def test_raises_when_no_wellness(tmp_path):
    memory, warehouse = _seed_corpus(tmp_path, omit_wellness=True)
    with pytest.raises(FileNotFoundError, match="wellness"):
        build_verdict_request_payload(
            memory_dir=memory, warehouse_dir=warehouse,
            target_date=date(2026, 5, 4))
