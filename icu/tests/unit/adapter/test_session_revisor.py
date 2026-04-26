"""Unit tests for adapter.session_revisor — HARD/MEDIUM 降载 + EASY/REST passthrough."""
from __future__ import annotations

from datetime import date

import pytest

from src.coach.adapter.session_revisor import revise_session
from src.coach.periodization.types import IntensityTier, SessionType
from src.coach.session_designer.types import DesignedSession


# ---------- Shared fixtures ----------

@pytest.fixture
def physiology() -> dict:
    return {"cp_watts": 288, "w_prime_joules": 20000, "athlete_ftp_set": 288}


@pytest.fixture
def durability() -> dict:
    return {"decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1}, "sample_size_rides": 28}


@pytest.fixture
def response_profile() -> dict:
    return {"types": {"vo2max": {"tolerance_class": "mid"}, "threshold": {"tolerance_class": "high"}}}


@pytest.fixture
def fixed_date() -> date:
    return date(2026, 4, 19)  # Sunday


# ---------- HARD bucket → recovery_spin ----------

@pytest.mark.parametrize("hard_type", [
    SessionType.THRESHOLD,
    SessionType.VO2MAX,
    SessionType.NEUROMUSCULAR,
    SessionType.RACE,
])
def test_revise_hard_returns_recovery_spin(
    hard_type, fixed_date, physiology, durability, response_profile,
):
    out = revise_session(
        original_type=hard_type, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert isinstance(out, DesignedSession)
    assert out.session_type is SessionType.RECOVERY
    assert out.date == "2026-04-19"
    assert out.day_of_week == "Sun"
    # template_name leaks via trace (composer 写入)
    assert out.trace is not None
    assert out.trace["template_name"] == "recovery_spin"
    # duration 落在 recovery_spin 模板的 (1800, 3600)s = 30-60min 范围
    assert 30 <= out.duration_min <= 60


# ---------- MEDIUM bucket → endurance_long_z2 ----------

def test_revise_tempo_returns_endurance_long_z2(
    fixed_date, physiology, durability, response_profile,
):
    out = revise_session(
        original_type=SessionType.TEMPO, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert isinstance(out, DesignedSession)
    assert out.session_type is SessionType.AEROBIC
    assert out.trace is not None
    assert out.trace["template_name"] == "endurance_long_z2"
    # endurance_long_z2 总时长下限 7200s = 120min（即使 target_tss=70 也压不下来）
    assert out.duration_min >= 120


# ---------- EASY / RECOVERY / REST → None ----------

@pytest.mark.parametrize("low_type", [
    SessionType.AEROBIC,
    SessionType.RECOVERY,
    SessionType.REST,
])
def test_revise_low_intensity_returns_none(
    low_type, fixed_date, physiology, durability, response_profile,
):
    out = revise_session(
        original_type=low_type, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert out is None


# ---------- Determinism / purity ----------

def test_revise_session_idempotent(
    fixed_date, physiology, durability, response_profile,
):
    """Same inputs → same outputs; no hidden state."""
    out1 = revise_session(
        original_type=SessionType.VO2MAX, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    out2 = revise_session(
        original_type=SessionType.VO2MAX, original_date=fixed_date,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert out1 == out2


def test_revise_session_keyword_only():
    """All parameters must be keyword-only — positional call must fail."""
    with pytest.raises(TypeError):
        revise_session(  # type: ignore[misc]
            SessionType.THRESHOLD, date(2026, 4, 19), {}, {}, {},
        )


def test_revise_session_passes_date_through(
    physiology, durability, response_profile,
):
    """day_of_week computed deterministically from original_date.weekday()."""
    monday = date(2026, 4, 13)  # Monday
    out = revise_session(
        original_type=SessionType.THRESHOLD, original_date=monday,
        physiology=physiology, durability=durability, response_profile=response_profile,
    )
    assert out is not None
    assert out.day_of_week == "Mon"
    assert out.date == "2026-04-13"
