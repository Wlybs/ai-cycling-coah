"""Unit tests for ledger types: AthleteStateRef, DecisionEntry, ULID helper."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.coach.ledger.types import (
    AthleteStateRef,
    DecisionEntry,
    DECISION_TYPES,
    generate_ulid,
    is_valid_ulid,
)


# ---------- AthleteStateRef ----------

def test_athlete_state_ref_roundtrip():
    ref = AthleteStateRef(
        ctl=72.3, atl=85.1, tsb=-12.8,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )
    js = ref.model_dump_json()
    loaded = AthleteStateRef.model_validate_json(js)
    assert loaded == ref


def test_athlete_state_ref_rejects_negative_w_prime():
    with pytest.raises(ValidationError):
        AthleteStateRef(
            ctl=72.3, atl=85.1, tsb=-12.8,
            w_prime=-100, phase="BUILD", week_of_year=16,
        )


def test_athlete_state_ref_week_of_year_range():
    AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                    w_prime=18000, phase="BASE", week_of_year=1)
    AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                    w_prime=18000, phase="BASE", week_of_year=53)
    with pytest.raises(ValidationError):
        AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                        w_prime=18000, phase="BASE", week_of_year=0)
    with pytest.raises(ValidationError):
        AthleteStateRef(ctl=70.0, atl=80.0, tsb=-10.0,
                        w_prime=18000, phase="BASE", week_of_year=54)


# ---------- DecisionEntry ----------

def _sample_state() -> AthleteStateRef:
    return AthleteStateRef(
        ctl=72.3, atl=85.1, tsb=-12.8,
        w_prime=18500, phase="BUILD", week_of_year=16,
    )


def test_decision_entry_minimal_fields():
    entry = DecisionEntry(
        entry_id=generate_ulid(),
        timestamp=datetime.now(timezone.utc),
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state_ref=_sample_state(),
        payload={"verdict": "green"},
    )
    assert entry.schema_version == 1
    assert entry.evidence_refs == []
    assert entry.superseded_by is None
    assert entry.confidence is None


def test_decision_entry_roundtrip_all_decision_types():
    for dt in DECISION_TYPES:
        entry = DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=datetime.now(timezone.utc),
            decision_type=dt,
            source=f"test.{dt}",
            athlete_state_ref=_sample_state(),
            payload={"_fixture": dt},
            confidence=0.5,
            evidence_refs=["physiology/cp_w_current.json"],
        )
        js = entry.model_dump_json()
        loaded = DecisionEntry.model_validate_json(js)
        assert loaded.decision_type == dt
        assert loaded.payload == {"_fixture": dt}


def test_decision_entry_rejects_unknown_decision_type():
    with pytest.raises(ValidationError):
        DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=datetime.now(timezone.utc),
            decision_type="made_up_type",
            source="test",
            athlete_state_ref=_sample_state(),
            payload={},
        )


def test_decision_entry_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        DecisionEntry(
            entry_id=generate_ulid(),
            timestamp=datetime(2026, 4, 19, 10, 0, 0),
            decision_type="adaptation_verdict",
            source="test",
            athlete_state_ref=_sample_state(),
            payload={},
        )


def test_decision_entry_confidence_range():
    base = dict(
        entry_id=generate_ulid(),
        timestamp=datetime.now(timezone.utc),
        decision_type="consensus_verdict",
        source="test",
        athlete_state_ref=_sample_state(),
        payload={},
    )
    DecisionEntry(**base, confidence=0.0)
    DecisionEntry(**base, confidence=1.0)
    with pytest.raises(ValidationError):
        DecisionEntry(**base, confidence=-0.01)
    with pytest.raises(ValidationError):
        DecisionEntry(**base, confidence=1.01)


def test_decision_entry_superseded_by_accepts_ulid():
    other = generate_ulid()
    entry = DecisionEntry(
        entry_id=generate_ulid(),
        timestamp=datetime.now(timezone.utc),
        decision_type="phase_transition",
        source="test",
        athlete_state_ref=_sample_state(),
        payload={},
        superseded_by=other,
    )
    assert entry.superseded_by == other


# ---------- ULID helper ----------

def test_ulid_is_26_char_crockford_base32():
    ulid = generate_ulid()
    assert len(ulid) == 26
    alphabet = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert set(ulid) <= alphabet


def test_ulid_uniqueness_within_burst():
    ulids = [generate_ulid() for _ in range(10_000)]
    assert len(set(ulids)) == 10_000


def test_ulid_monotonic_across_ms():
    import time
    a = generate_ulid()
    time.sleep(0.002)
    b = generate_ulid()
    assert b[:10] > a[:10]


def test_is_valid_ulid():
    assert is_valid_ulid(generate_ulid()) is True
    assert is_valid_ulid("TOO_SHORT") is False
    assert is_valid_ulid("I" * 26) is False
    assert is_valid_ulid("L" * 26) is False


def test_decision_types_matches_blueprint():
    expected = {
        "phase_transition", "macro_plan_generated", "meso_block_created",
        "micro_cycle_generated", "weekly_plan_assembled",
        "consensus_verdict", "adaptation_verdict", "adaptation_applied",
    }
    assert set(DECISION_TYPES) == expected
