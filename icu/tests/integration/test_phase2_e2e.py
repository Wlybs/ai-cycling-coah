"""Phase 2 end-to-end integration test.

Tests the full pipeline: mocked warehouse → periodization refresh →
generate_plan_v2 → WeeklyPlan JSON artifact.

4 scenarios:
1. BUILD phase (race far) → high TSS, ≥1 HARD day
2. TAPER phase (race in <10 days) → low TSS, REST day before race
3. CP vs FTP: when CP < FTP, power ranges respect CP boundaries
4. Report JSON round-trips through Pydantic validation
"""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.coach.session_designer.generator_v2 import generate_plan_v2
from src.coach.session_designer.types import WeeklyPlan


def _seed_warehouse_and_memory(
    tmp_path: Path,
    race_in_days: int = 56,
    cp_watts: int = 280,
    ftp_watts: int = 288,
    knee_flag: str | None = None,
) -> tuple[Path, Path]:
    """Seed complete tmp_path-based warehouse and memory trees.

    Args:
        tmp_path: Temporary directory root
        race_in_days: Days from 2026-04-18 until race (default 56 = BUILD phase)
        cp_watts: Critical power in watts
        ftp_watts: Functional threshold power (for athlete.json fallback)
        knee_flag: Optional knee-loading flag ("caution", "monitor", etc.)

    Returns:
        (warehouse_dir, memory_dir) paths
    """
    # Warehouse structure
    warehouse = tmp_path / "icu_data_warehouse"
    (warehouse / "2_Wellness").mkdir(parents=True)
    (warehouse / "8_Events").mkdir(parents=True)
    (warehouse / "1_Profile").mkdir(parents=True)

    # Wellness history (CTL progression)
    wellness_entries = [
        {"id": f"2026-03-{d:02d}", "ctl": 80 + d * 0.4, "atl": 90}
        for d in range(1, 32)
    ] + [
        {"id": f"2026-04-{d:02d}", "ctl": 92 + d * 0.2, "atl": 95}
        for d in range(1, 19)
    ]
    (warehouse / "2_Wellness" / "wellness_history.json").write_text(
        json.dumps(wellness_entries), encoding="utf-8"
    )

    # Events (race calendar)
    race_date = date(2026, 4, 18) + timedelta(days=race_in_days)
    events = [
        {
            "id": 1,
            "category": "RACE",
            "name": "Goal",
            "start_date_local": f"{race_date.isoformat()}T08:00:00",
            "priority": "A",
        }
    ]
    (warehouse / "8_Events" / "events.json").write_text(
        json.dumps(events), encoding="utf-8"
    )

    # Athlete profile
    (warehouse / "1_Profile" / "athlete.json").write_text(
        json.dumps({"ftp": ftp_watts, "hr_max": 195, "weight": 62}),
        encoding="utf-8",
    )

    # Memory structure
    mem = tmp_path / "coach_memory"
    (mem / "physiology").mkdir(parents=True)
    (mem / "deep_analysis").mkdir(parents=True)

    # CP and W' data
    (mem / "physiology" / "cp_w_current.json").write_text(
        json.dumps(
            {
                "cp_watts": cp_watts,
                "w_prime_joules": 22000,
                "fit_r_squared": 0.95,
                "athlete_ftp_set": ftp_watts,
            }
        ),
        encoding="utf-8",
    )

    # Durability (empty for this test)
    (mem / "physiology" / "durability.json").write_text(
        json.dumps({}), encoding="utf-8"
    )

    # Response profile (includes knee flag)
    response = {
        "types": {},
        "knee_loading": {
            "flag": knee_flag,
            "standing_climb_minutes_90d": 0,
        },
    }
    (mem / "physiology" / "response_profile.json").write_text(
        json.dumps(response), encoding="utf-8"
    )

    return warehouse, mem


@pytest.mark.integration
def test_e2e_build_week_high_tss_with_hard(tmp_path: Path) -> None:
    """Scenario 1: BUILD phase (race in 56 days) → high TSS + ≥1 HARD.

    Assertions:
    - Phase detected as BUILD (or similar)
    - weekly_tss_target >= 350
    - At least 1 day with stimulus intensity (Tempo, VO2max, Threshold, etc.)
    - All 4 report paths populated and valid JSON
    - WeeklyPlan round-trips through Pydantic validation
    """
    warehouse, mem = _seed_warehouse_and_memory(
        tmp_path, race_in_days=56, cp_watts=280, ftp_watts=288
    )
    reports = tmp_path / "reports"

    result = generate_plan_v2(
        week_start=date(2026, 4, 20),
        week_end=date(2026, 4, 26),
        warehouse_dir=warehouse,
        memory_dir=mem,
        reports_dir=reports,
        push_to_icu=False,
    )

    # Status OK
    assert result.status == "ok", f"Expected status ok, got: {result.error}"

    # All 4 paths populated
    assert result.plan_json_path is not None
    assert result.plan_md_path is not None
    assert result.trace_path is not None
    assert result.prose_prompt_path is not None

    # Load and validate plan JSON
    plan_doc = json.loads(
        Path(result.plan_json_path).read_text(encoding="utf-8")
    )
    plan = WeeklyPlan.model_validate(plan_doc)

    # 7 days
    assert len(plan.days) == 7

    # HIGH TSS for BUILD phase
    assert plan.weekly_tss_target >= 350, f"Expected TSS >= 350, got {plan.weekly_tss_target}"

    # At least 1 stimulus/hard day (Tempo, VO2max, Threshold, Anaerobic, etc.)
    hard_types = {"Tempo", "VO2max", "Threshold", "Anaerobic", "Neuromuscular"}
    hard_count = sum(
        1 for d in plan.days if d.training_type in hard_types
    )
    assert hard_count >= 1, f"Expected >= 1 HARD day, got {hard_count} (types seen: {set(d.training_type for d in plan.days)})"

    # Periodization snapshot exists and indicates BUILD phase
    snap_path = mem / "periodization" / "periodization_current.json"
    assert snap_path.exists()
    snap_doc = json.loads(snap_path.read_text(encoding="utf-8"))
    # Phase should be BUILD in 56-day scenario (CTL=92+)
    assert snap_doc["current_phase"] == "BUILD", \
        f"Expected BUILD phase, got {snap_doc['current_phase']}"


@pytest.mark.integration
def test_e2e_taper_week_low_tss_with_rest(tmp_path: Path) -> None:
    """Scenario 2: TAPER phase (race in 5 days) → low TSS + reduced load.

    Assertions:
    - Phase detected as TAPER
    - weekly_tss_target < 350 (significantly less than BUILD)
    - Proportion of REST/Recovery days is higher than BUILD
    - Day before race (Fri 2026-04-24) must be Rest
    - Plan JSON is valid and round-trips
    """
    warehouse, mem = _seed_warehouse_and_memory(
        tmp_path, race_in_days=5, cp_watts=280, ftp_watts=288
    )
    reports = tmp_path / "reports"

    result = generate_plan_v2(
        week_start=date(2026, 4, 20),
        week_end=date(2026, 4, 26),
        warehouse_dir=warehouse,
        memory_dir=mem,
        reports_dir=reports,
        push_to_icu=False,
    )

    assert result.status == "ok", f"Expected status ok, got: {result.error}"

    # Load and validate plan JSON
    plan_doc = json.loads(
        Path(result.plan_json_path).read_text(encoding="utf-8")
    )
    plan = WeeklyPlan.model_validate(plan_doc)

    # TAPER TSS must be significantly lower
    assert plan.weekly_tss_target < 350, \
        f"TAPER TSS should be < 350, got {plan.weekly_tss_target}"

    # Periodization snapshot indicates TAPER phase
    snap_path = mem / "periodization" / "periodization_current.json"
    snap_doc = json.loads(snap_path.read_text(encoding="utf-8"))
    assert snap_doc["current_phase"] == "TAPER", \
        f"Expected TAPER phase, got {snap_doc['current_phase']}"

    # TAPER should have more recovery days (Rest + Recovery types) than BUILD phase
    recovery_types = {"Rest", "Recovery"}
    recovery_count = sum(
        1 for d in plan.days if d.training_type in recovery_types
    )
    # In TAPER, expect at least 50% recovery days (≥3 out of 7)
    assert recovery_count >= 3, \
        f"TAPER should have >= 3 recovery days, got {recovery_count}"

    # Day before race (2026-04-25 race → 2026-04-24 Fri is day before) must be Rest
    day_before_race = date(2026, 4, 24)
    day_before_day = next(
        (d for d in plan.days if d.date == str(day_before_race)),
        None
    )
    assert day_before_day is not None, \
        f"Could not find {day_before_race} in plan days"
    assert day_before_day.training_type == "Rest", \
        f"Day before race must be Rest, got {day_before_day.training_type}"


@pytest.mark.integration
def test_e2e_cp_used_not_ftp_when_different(tmp_path: Path) -> None:
    """Scenario 3: CP < FTP → power ranges use CP boundaries, not FTP.

    Seed: cp_watts=260, ftp_watts=288
    Expected: Tempo/Threshold power_range upper bounds < 320W (would be >330W if FTP were used).

    Assertions:
    - For stimulus days (Tempo, Threshold), power_range_w upper bound < 320W
    - Confirms CP-based generation, not FTP-based
    """
    warehouse, mem = _seed_warehouse_and_memory(
        tmp_path, race_in_days=56, cp_watts=260, ftp_watts=288
    )
    reports = tmp_path / "reports"

    result = generate_plan_v2(
        week_start=date(2026, 4, 20),
        week_end=date(2026, 4, 26),
        warehouse_dir=warehouse,
        memory_dir=mem,
        reports_dir=reports,
        push_to_icu=False,
    )

    assert result.status == "ok"

    # Load plan
    plan_doc = json.loads(
        Path(result.plan_json_path).read_text(encoding="utf-8")
    )
    plan = WeeklyPlan.model_validate(plan_doc)

    # Check power ranges on stimulus days
    stimulus_types = {"Tempo", "Threshold", "VO2max", "Anaerobic"}
    checked_days = 0
    for day in plan.days:
        if day.training_type in stimulus_types:
            power_range = day.power_range_w
            if power_range:
                checked_days += 1
                # Parse "200-300W" format
                parts = power_range.replace("W", "").split("-")
                high_power = int(parts[-1])
                # If using FTP=288, upper bound would be ~330W (288 * 1.15)
                # Using CP=260, should be ~312W (260 * 1.20)
                # Real cap should be < 320W
                assert high_power < 320, \
                    f"CP-based limit should be < 320W, got {high_power}W (indicates FTP used)"
    # Ensure at least one stimulus day with power range was checked (prevent vacuous pass)
    assert checked_days >= 1, \
        "no stimulus day with power_range_w to check — seed likely produced none, test would vacuously pass"


@pytest.mark.integration
def test_e2e_report_files_pydantic_valid(tmp_path: Path) -> None:
    """Scenario 4: Report JSON artifacts are Pydantic-valid.

    Assertions:
    - WeeklyPlan.model_validate(doc) succeeds without raising
    - All required fields present and typed correctly
    """
    warehouse, mem = _seed_warehouse_and_memory(
        tmp_path, race_in_days=56, cp_watts=280, ftp_watts=288
    )
    reports = tmp_path / "reports"

    result = generate_plan_v2(
        week_start=date(2026, 4, 20),
        week_end=date(2026, 4, 26),
        warehouse_dir=warehouse,
        memory_dir=mem,
        reports_dir=reports,
        push_to_icu=False,
    )

    assert result.status == "ok"

    # Load and validate plan JSON
    doc = json.loads(
        Path(result.plan_json_path).read_text(encoding="utf-8")
    )

    # This should not raise; if it does, the JSON structure is invalid
    plan = WeeklyPlan.model_validate(doc)

    # Basic sanity checks
    assert plan.week_start == "2026-04-20"
    assert plan.week_end == "2026-04-26"
    assert isinstance(plan.weekly_tss_target, int)
    assert isinstance(plan.days, list)
    assert len(plan.days) == 7

    # Each day is a DayPlanV2 with required fields
    for i, day in enumerate(plan.days):
        assert day.day_of_week is not None
        assert day.training_type is not None
        assert day.name is not None
        assert day.duration_min >= 0
        assert day.target_tss >= 0
