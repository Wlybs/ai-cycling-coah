"""Unit tests for adapter types: SignalSnapshot, AdaptationVerdict."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.coach.adapter.types import (
    AdaptationVerdict,
    RECOMMENDED_ACTIONS,
    SignalSnapshot,
    VERDICT_VALUES,
)


# ---------- SignalSnapshot ----------

def test_signal_snapshot_roundtrip(fixed_utc_now):
    snap = SignalSnapshot(
        captured_at=fixed_utc_now,
        hrv_ms=68.0,
        resting_hr_bpm=52,
        sleep_hours=7.4,
        soreness_score=3,
    )
    js = snap.model_dump_json()
    loaded = SignalSnapshot.model_validate_json(js)
    assert loaded == snap


def test_signal_snapshot_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        SignalSnapshot(
            captured_at=datetime(2026, 4, 19, 10, 0, 0),  # no tzinfo
            hrv_ms=68.0, resting_hr_bpm=52,
            sleep_hours=7.4, soreness_score=3,
        )


def test_signal_snapshot_soreness_range(fixed_utc_now):
    # soreness scale 1 (worst) .. 4 (best) — Intervals.icu wellness convention
    SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                   resting_hr_bpm=50, sleep_hours=7.0, soreness_score=1)
    SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                   resting_hr_bpm=50, sleep_hours=7.0, soreness_score=4)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=50, sleep_hours=7.0, soreness_score=0)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=50, sleep_hours=7.0, soreness_score=5)


def test_signal_snapshot_accepts_none_soreness(fixed_utc_now):
    # v3.0.1: real ICU wellness has soreness=null when athlete didn't log it.
    # Schema must accept None; classifier treats None as green ("no concern logged").
    snap = SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                          resting_hr_bpm=50, sleep_hours=7.0, soreness_score=None)
    assert snap.soreness_score is None
    js = snap.model_dump_json()
    loaded = SignalSnapshot.model_validate_json(js)
    assert loaded == snap


def test_signal_snapshot_rejects_negative_physiology(fixed_utc_now):
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=-1.0,
                       resting_hr_bpm=50, sleep_hours=7.0, soreness_score=3)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=-1, sleep_hours=7.0, soreness_score=3)
    with pytest.raises(ValidationError):
        SignalSnapshot(captured_at=fixed_utc_now, hrv_ms=60.0,
                       resting_hr_bpm=50, sleep_hours=-0.1, soreness_score=3)


# ---------- AdaptationVerdict ----------

def _signal_summary_all(verdict: str) -> dict[str, str]:
    return {"hrv": verdict, "resting_hr": verdict,
            "sleep": verdict, "soreness": verdict}


def test_verdict_values_locked():
    # 00-index.md locks {green, yellow, red} (lowercase) — adding a 4th requires ADR.
    assert set(VERDICT_VALUES) == {"green", "yellow", "red"}


def test_recommended_actions_whitelist():
    # HUMAN_GATE_ON_ICU_WRITE: no value here may imply auto-push.
    assert set(RECOMMENDED_ACTIONS) == {
        "none", "nudge_only", "propose_replacement", "rest_48h",
    }


def test_adaptation_verdict_minimal_green():
    v = AdaptationVerdict(
        verdict="green",
        signal_summary=_signal_summary_all("green"),
        severity_score=0.0,
        recommended_action="none",
    )
    assert v.triggered_rules == []
    assert v.guardrails_hit == []
    assert v.notes is None


def test_adaptation_verdict_roundtrip_red():
    v = AdaptationVerdict(
        verdict="red",
        signal_summary={"hrv": "red", "resting_hr": "yellow",
                        "sleep": "red", "soreness": "yellow"},
        severity_score=0.85,
        recommended_action="propose_replacement",
        triggered_rules=["hrv_red_threshold", "sleep_debt_acute"],
        guardrails_hit=[],
        notes="HRV -12.3% vs 28d mean",
    )
    js = v.model_dump_json()
    loaded = AdaptationVerdict.model_validate_json(js)
    assert loaded == v


def test_adaptation_verdict_severity_range():
    base = dict(
        verdict="green",
        signal_summary=_signal_summary_all("green"),
        recommended_action="none",
    )
    AdaptationVerdict(**base, severity_score=0.0)
    AdaptationVerdict(**base, severity_score=1.0)
    with pytest.raises(ValidationError):
        AdaptationVerdict(**base, severity_score=-0.01)
    with pytest.raises(ValidationError):
        AdaptationVerdict(**base, severity_score=1.01)


def test_adaptation_verdict_rejects_unknown_verdict():
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="amber",  # not in {green, yellow, red}
            signal_summary=_signal_summary_all("green"),
            severity_score=0.0,
            recommended_action="none",
        )


def test_adaptation_verdict_rejects_unknown_action():
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="red",
            signal_summary=_signal_summary_all("red"),
            severity_score=1.0,
            recommended_action="auto_push_to_icu",  # forbidden
        )


def test_adaptation_verdict_signal_summary_keys_complete():
    # All 4 signal keys must be present — protects downstream prompt rendering.
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="green",
            signal_summary={"hrv": "green"},  # missing 3 keys
            severity_score=0.0,
            recommended_action="none",
        )


def test_adaptation_verdict_signal_summary_values_locked():
    with pytest.raises(ValidationError):
        AdaptationVerdict(
            verdict="green",
            signal_summary={"hrv": "fine", "resting_hr": "green",
                            "sleep": "green", "soreness": "green"},
            severity_score=0.0,
            recommended_action="none",
        )
