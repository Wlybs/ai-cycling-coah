import json
from datetime import date
from pathlib import Path

from src.coach.periodization.snapshot_io import (
    write_phase_current, write_macro_plan, write_meso_block,
    write_micro_cycle, write_periodization_snapshot,
    load_periodization_snapshot,
)
from src.coach.periodization.types import (
    Phase, PhaseIntent, MacroPlan, MacroWindow, MesoBlock, MicroCycle,
    DayIntent, IntensityTier, PeriodizationSnapshot,
)


def _make_intent(phase=Phase.BUILD):
    return PhaseIntent(
        phase=phase, primary_adaptation="threshold_capacity",
        weekly_tss_target=500,
        intensity_distribution_pct={"low": 75, "mid": 15, "high": 10},
        rest_days_per_week=1, rationale="test",
    )


def _make_micro(phase=Phase.BUILD, week_start=date(2026, 4, 20)):
    return MicroCycle(
        week_start=week_start, week_end=date(2026, 4, 26),
        phase=phase, intent=_make_intent(phase),
        days=[DayIntent(day_of_week=d, tier=IntensityTier.EASY,
                        target_tss=40, session_hint="x")
              for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]],
        weekly_tss_target=450,
    )


def test_write_phase_current_creates_file(tmp_path):
    base = tmp_path / "coach_memory" / "periodization"
    path = write_phase_current(
        base_dir=base, phase=Phase.BUILD,
        reasons=["CTL slope +0.3/d over 4w", "no race within 4w"],
        now_iso="2026-04-18T00:00:00Z",
    )
    assert Path(path).exists()
    doc = json.loads(Path(path).read_text())
    assert doc["current_phase"] == "BUILD"
    assert "CTL slope" in doc["reasons"][0]


def test_write_and_load_snapshot_roundtrip(tmp_path):
    base = tmp_path / "coach_memory" / "periodization"
    intent = _make_intent()
    macro = MacroPlan(
        generated_at="2026-04-18T00:00:00Z",
        season_end_date=date(2026, 9, 30),
        windows=[MacroWindow(phase=Phase.BUILD, start_date=date(2026, 4, 1),
                             end_date=date(2026, 4, 28), intent=intent)],
    )
    meso = MesoBlock(
        pattern="3:1",
        block_start=date(2026, 4, 6), block_end=date(2026, 4, 26),
        weekly_load_multipliers=[1.0, 1.05, 1.1, 0.7], phase=Phase.BUILD,
    )
    micro = _make_micro()
    snap = PeriodizationSnapshot(
        generated_at="2026-04-18T00:00:00Z",
        current_phase=Phase.BUILD, macro=macro, meso=meso, micro=micro,
    )
    path = write_periodization_snapshot(base, snap)
    loaded = load_periodization_snapshot(base)
    assert loaded is not None
    assert loaded.current_phase is Phase.BUILD
    assert loaded.micro.weekly_tss_target == 450
    # 同时写了 micro_cycle_YYYY-WW.json
    assert any((base.glob("micro_cycle_*.json")))


def test_load_missing_returns_none(tmp_path):
    assert load_periodization_snapshot(tmp_path / "nope") is None
