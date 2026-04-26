"""Threshold golden-value tests for adapter.rules — 4 signals × 3 verdicts + 2 guardrails."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.coach.adapter.rules import (
    HRV_DEVIATION_RED_PCT,
    HRV_DEVIATION_YELLOW_PCT,
    RESTING_HR_RED_DELTA_BPM,
    RESTING_HR_YELLOW_DELTA_BPM,
    SLEEP_RED_HOURS,
    SLEEP_YELLOW_HOURS,
    SORENESS_RED_SCORE,
    SORENESS_YELLOW_SCORE,
    TSB_ANOMALY_THRESHOLD,
    CONSECUTIVE_RED_LIMIT,
    _classify_hrv,
    _classify_resting_hr,
    _classify_sleep,
    _classify_soreness,
    _consecutive_red_count,
    _tsb_anomaly_hit,
    _severity_score,
)
from src.coach.adapter.types import SignalSnapshot
from src.coach.ledger.types import AthleteStateRef, DecisionEntry, generate_ulid


# ---------- HRV ----------

@pytest.mark.parametrize("dev_pct,expected", [
    (-2.0, "green"),                                # well within ±5%
    (HRV_DEVIATION_YELLOW_PCT + 0.01, "green"),     # boundary just above yellow
    (HRV_DEVIATION_YELLOW_PCT, "yellow"),           # boundary inclusive
    (-7.5, "yellow"),                               # mid-yellow
    (HRV_DEVIATION_RED_PCT, "red"),                 # boundary inclusive
    (-15.0, "red"),                                 # well below red
])
def test_classify_hrv(dev_pct, expected):
    assert _classify_hrv(deviation_pct=dev_pct) == expected


# ---------- Resting HR ----------

@pytest.mark.parametrize("delta_bpm,expected", [
    (0, "green"),
    (RESTING_HR_YELLOW_DELTA_BPM - 1, "green"),
    (RESTING_HR_YELLOW_DELTA_BPM, "yellow"),
    (RESTING_HR_RED_DELTA_BPM - 1, "yellow"),
    (RESTING_HR_RED_DELTA_BPM, "red"),
    (15, "red"),
])
def test_classify_resting_hr(delta_bpm, expected):
    assert _classify_resting_hr(delta_bpm=delta_bpm) == expected


# ---------- Sleep ----------

@pytest.mark.parametrize("hours,expected", [
    (8.0, "green"),
    (SLEEP_YELLOW_HOURS, "green"),                  # ≥ yellow boundary inclusive on green side
    (SLEEP_YELLOW_HOURS - 0.01, "yellow"),
    (SLEEP_RED_HOURS, "yellow"),                    # red boundary: < SLEEP_RED → red
    (SLEEP_RED_HOURS - 0.01, "red"),
    (4.0, "red"),
])
def test_classify_sleep(hours, expected):
    assert _classify_sleep(sleep_hours=hours) == expected


# ---------- Soreness (1=worst..4=best) ----------

@pytest.mark.parametrize("score,expected", [
    (4, "green"),
    (SORENESS_YELLOW_SCORE + 1, "green"),
    (SORENESS_YELLOW_SCORE, "yellow"),
    (SORENESS_RED_SCORE, "red"),
    (1, "red"),
])
def test_classify_soreness(score, expected):
    assert _classify_soreness(score=score) == expected


# ---------- Severity weighted score ----------

def test_severity_score_all_green():
    s = _severity_score({"hrv": "green", "resting_hr": "green",
                         "sleep": "green", "soreness": "green"})
    assert s == 0.0


def test_severity_score_all_red():
    s = _severity_score({"hrv": "red", "resting_hr": "red",
                         "sleep": "red", "soreness": "red"})
    assert s == pytest.approx(1.0)


def test_severity_score_mixed_is_in_unit_interval():
    s = _severity_score({"hrv": "red", "resting_hr": "yellow",
                         "sleep": "green", "soreness": "yellow"})
    assert 0.0 < s < 1.0


# ---------- Guardrail 1: consecutive red ----------

def _verdict_entry(state: AthleteStateRef, verdict: str,
                   ts: datetime) -> DecisionEntry:
    return DecisionEntry(
        entry_id=generate_ulid(),
        timestamp=ts,
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state_ref=state,
        payload={"verdict": verdict},
    )


class _FrozenDatetime(datetime):
    _frozen: datetime

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        if tz is None:
            return cls._frozen.replace(tzinfo=None)
        return cls._frozen.astimezone(tz)


@pytest.fixture
def freeze_now(monkeypatch, fixed_utc_now):
    """Freeze datetime.now() inside src.coach.adapter.rules to fixed_utc_now."""
    import src.coach.adapter.rules as rules_mod

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            if tz is None:
                return fixed_utc_now.replace(tzinfo=None)
            return fixed_utc_now.astimezone(tz)

    monkeypatch.setattr(rules_mod, "datetime", _Frozen)
    return fixed_utc_now


def test_consecutive_red_count_zero(baseline_state, fixed_utc_now, freeze_now):
    history = [
        _verdict_entry(baseline_state, "green", fixed_utc_now - timedelta(days=i))
        for i in range(1, 5)
    ]
    assert _consecutive_red_count(history) == 0


def test_consecutive_red_count_three_in_last_four_days(baseline_state, fixed_utc_now, freeze_now):
    history = [
        _verdict_entry(baseline_state, "red",   fixed_utc_now - timedelta(days=1)),
        _verdict_entry(baseline_state, "red",   fixed_utc_now - timedelta(days=2)),
        _verdict_entry(baseline_state, "green", fixed_utc_now - timedelta(days=3)),
        _verdict_entry(baseline_state, "red",   fixed_utc_now - timedelta(days=4)),
    ]
    # 3 reds within 4-day lookback → triggers when today is also red
    assert _consecutive_red_count(history) >= CONSECUTIVE_RED_LIMIT - 1


def test_consecutive_red_count_ignores_old_entries(baseline_state, fixed_utc_now, freeze_now):
    history = [
        _verdict_entry(baseline_state, "red", fixed_utc_now - timedelta(days=10)),
        _verdict_entry(baseline_state, "red", fixed_utc_now - timedelta(days=11)),
        _verdict_entry(baseline_state, "red", fixed_utc_now - timedelta(days=12)),
    ]
    assert _consecutive_red_count(history) == 0


# ---------- Guardrail 2: TSB anomaly ----------

def test_tsb_anomaly_hit_below_threshold(stressed_state):
    assert _tsb_anomaly_hit(stressed_state) is True


def test_tsb_anomaly_not_hit_baseline(baseline_state):
    assert _tsb_anomaly_hit(baseline_state) is False


def test_tsb_anomaly_threshold_is_negative_thirty():
    # Locked default — see rules.py docstring for derivation
    assert TSB_ANOMALY_THRESHOLD == -30.0
