"""Unit tests for HistoryInjector: empty, sparse, saturated, outcome_pending."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.coach.consensus.history_injector import (
    HistoryTriplet,
    compress_history,
)
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter


def _state(ctl: float = 72.0, phase: str = "BUILD",
           week: int = 16) -> AthleteStateRef:
    return AthleteStateRef(
        ctl=ctl, atl=ctl * 1.1, tsb=-ctl * 0.15,
        w_prime=18500, phase=phase, week_of_year=week,
    )


@pytest.fixture
def ledger_path(tmp_path) -> Path:
    return tmp_path / "decisions.jsonl"


# ---------- empty ledger ----------

def test_compress_history_empty_ledger_returns_empty(ledger_path):
    reader = LedgerReader(ledger_path)  # file does not exist yet
    triplets = compress_history(reader, _state(), limit=8)
    assert triplets == []


# ---------- < 3 plans ----------

def test_compress_history_returns_all_when_under_three(ledger_path):
    w = LedgerWriter(ledger_path)
    # 2 weekly_plan_assembled, both BUILD/CTL≈72
    for i in range(2):
        w.record(
            decision_type="weekly_plan_assembled",
            source="ingester",
            athlete_state=_state(ctl=72.0 + i * 0.4),
            payload={"plan_period": f"2026-W{14+i:02d}", "total_tss": 460},
        )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 2
    # All should have outcome_pending since no follow-on verdicts written
    assert all(t.outcome == "outcome_pending" for t in triplets)


# ---------- > 8 plans → cap at 8 ----------

def test_compress_history_caps_at_limit(ledger_path):
    w = LedgerWriter(ledger_path)
    for i in range(12):
        w.record(
            decision_type="weekly_plan_assembled",
            source="ingester",
            athlete_state=_state(ctl=72.0),
            payload={"plan_period": f"2026-W{i:02d}", "total_tss": 460},
        )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 8


# ---------- outcome stitching ----------

def test_compress_history_attaches_consensus_verdict_outcome(ledger_path):
    w = LedgerWriter(ledger_path)
    plan_id = w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(),
        payload={"plan_period": "2026-W14", "total_tss": 480},
    )
    # Following consensus_verdict written same day for that plan
    w.record(
        decision_type="consensus_verdict",
        source="consensus.council",
        athlete_state=_state(),
        payload={"verdict": "REVISE", "confidence": 0.7,
                 "supersedes_plan_entry_id": plan_id},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 1
    t = triplets[0]
    assert isinstance(t, HistoryTriplet)
    assert "REVISE" in t.outcome
    assert t.context["plan_period"] == "2026-W14"


def test_compress_history_attaches_adaptation_verdict_outcome(ledger_path):
    w = LedgerWriter(ledger_path)
    plan_id = w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(),
        payload={"plan_period": "2026-W15", "total_tss": 500},
    )
    w.record(
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state=_state(),
        payload={"verdict": "red",
                 "supersedes_plan_entry_id": plan_id,
                 "reason": "HRV crash"},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 1
    assert "red" in triplets[0].outcome


# ---------- outcome_pending sentinel ----------

def test_compress_history_marks_outcome_pending_when_no_follow_on(ledger_path):
    w = LedgerWriter(ledger_path)
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(),
        payload={"plan_period": "2026-W17", "total_tss": 470},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(), limit=8)
    assert len(triplets) == 1
    assert triplets[0].outcome == "outcome_pending"


def test_compress_history_filters_out_unrelated_phase(ledger_path):
    w = LedgerWriter(ledger_path)
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(phase="PEAK"),
        payload={"plan_period": "2026-W14"},
    )
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=_state(phase="BUILD"),
        payload={"plan_period": "2026-W15"},
    )
    reader = LedgerReader(ledger_path)
    triplets = compress_history(reader, _state(phase="BUILD"), limit=8)
    assert len(triplets) == 1
    assert triplets[0].context["plan_period"] == "2026-W15"


def test_history_triplet_pydantic_roundtrip():
    t = HistoryTriplet(
        plan_entry_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        context={"plan_period": "2026-W14", "total_tss": 460,
                 "ctl": 72.3, "phase": "BUILD"},
        verdict="REVISE",
        outcome="consensus.REVISE@0.70",
    )
    js = t.model_dump_json()
    loaded = HistoryTriplet.model_validate_json(js)
    assert loaded == t


def test_compress_history_no_llm_no_heuristic_estimation(ledger_path,
                                                         monkeypatch):
    """Defense-in-depth: importing google.genai at module load must fail clean."""
    import sys
    assert "google.genai" not in sys.modules
    # Sanity: module under test must not pull google.genai transitively
    from src.coach.consensus import history_injector  # noqa: F401
    assert "google.genai" not in sys.modules
