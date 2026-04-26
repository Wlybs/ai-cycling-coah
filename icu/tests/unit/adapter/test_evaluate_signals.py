"""End-to-end tests for evaluate_signals — happy path + 4 boundary scenarios."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.coach.adapter.rules import evaluate_signals
from src.coach.adapter.types import SignalSnapshot
from src.coach.ledger.types import AthleteStateRef, DecisionEntry, generate_ulid


def _snap(fixed_utc_now: datetime, *,
          hrv: float = 68.0, hr: int = 52,
          sleep: float = 7.4, sore: int = 3) -> SignalSnapshot:
    return SignalSnapshot(
        captured_at=fixed_utc_now,
        hrv_ms=hrv, resting_hr_bpm=hr,
        sleep_hours=sleep, soreness_score=sore,
    )


# ---------- happy path ----------

def test_happy_path_all_green(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now)
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "green"
    assert v.severity_score == 0.0
    assert v.recommended_action == "none"
    assert v.triggered_rules == []
    assert v.guardrails_hit == []
    assert set(v.signal_summary.values()) == {"green"}


# ---------- yellow path ----------

def test_yellow_when_sleep_short(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now, sleep=6.0)  # < 7.0 → yellow, ≥ 5.5 → not red
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "yellow"
    assert v.recommended_action == "nudge_only"
    assert v.signal_summary["sleep"] == "yellow"
    assert 0.0 < v.severity_score < 1.0


# ---------- red path: single signal ----------

def test_red_when_hrv_collapses(fixed_utc_now, baseline_state):
    # HRV -15% vs 28d mean → red
    snap = _snap(fixed_utc_now, hrv=68.0 * 0.85)
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "red"
    assert v.recommended_action == "propose_replacement"
    assert "hrv_red_threshold" in v.triggered_rules
    assert v.guardrails_hit == []


# ---------- guardrail 1: TSB anomaly forces red ----------

def test_tsb_anomaly_forces_red_even_with_green_signals(fixed_utc_now,
                                                        stressed_state):
    snap = _snap(fixed_utc_now)  # all green signals
    v = evaluate_signals(
        snap, state=stressed_state,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "red"
    assert "tsb_anomaly" in v.guardrails_hit
    assert v.severity_score >= 0.1  # bumped by guardrail


# ---------- guardrail 2: consecutive red escalates to rest_48h ----------

def test_consecutive_red_escalates_to_rest_48h(fixed_utc_now, baseline_state,
                                               freeze_now):
    # 2 prior red entries within last 4 days; today HRV crash → 3rd red → escalate
    history = [
        DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=fixed_utc_now - timedelta(days=i),
            decision_type="adaptation_verdict",
            source="adapter.daily",
            athlete_state_ref=baseline_state,
            payload={"verdict": "red"},
        )
        for i in (1, 2)
    ]
    snap = _snap(fixed_utc_now, hrv=68.0 * 0.85)  # red
    v = evaluate_signals(
        snap, state=baseline_state, history=history,
        hrv_28d_mean_ms=68.0, resting_hr_28d_mean_bpm=52.0,
    )
    assert v.verdict == "red"
    assert v.recommended_action == "rest_48h"
    assert "consecutive_red_escalation" in v.guardrails_hit


# ---------- baseline missing → graceful fallback ----------

def test_missing_baselines_skips_those_signals(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now, hrv=10.0, hr=120)  # would be RED if baselined
    v = evaluate_signals(
        snap, state=baseline_state,
        hrv_28d_mean_ms=None, resting_hr_28d_mean_bpm=None,
    )
    # Without baselines, hrv/resting_hr default to green; sleep/soreness still active.
    assert v.signal_summary["hrv"] == "green"
    assert v.signal_summary["resting_hr"] == "green"
    assert v.verdict in {"green", "yellow", "red"}  # depends on sleep/soreness


# ---------- determinism (pure function) ----------

def test_evaluate_signals_is_pure(fixed_utc_now, baseline_state):
    snap = _snap(fixed_utc_now, hrv=68.0 * 0.85)
    v1 = evaluate_signals(snap, state=baseline_state,
                          hrv_28d_mean_ms=68.0,
                          resting_hr_28d_mean_bpm=52.0)
    v2 = evaluate_signals(snap, state=baseline_state,
                          hrv_28d_mean_ms=68.0,
                          resting_hr_28d_mean_bpm=52.0)
    assert v1 == v2
