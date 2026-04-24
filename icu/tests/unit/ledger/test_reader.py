"""Unit tests for LedgerReader: query, query_similar, trace_chain, corruption tolerance."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter


def _state(ctl: float = 72.0, phase: str = "BUILD", week: int = 16) -> AthleteStateRef:
    return AthleteStateRef(
        ctl=ctl, atl=ctl * 1.1, tsb=-ctl * 0.15,
        w_prime=18500, phase=phase, week_of_year=week,
    )


# ---------- query ----------

def test_query_returns_empty_on_missing_file(tmp_path):
    r = LedgerReader(tmp_path / "not_there.jsonl")
    assert r.query() == []


def test_query_returns_all_entries_default(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    for i in range(3):
        w.record(decision_type="adaptation_verdict", source="test",
                 athlete_state=sample_state, payload={"i": i})
    r = LedgerReader(ledger_path)
    entries = r.query()
    assert len(entries) == 3
    assert [e.payload["i"] for e in entries] == [0, 1, 2]


def test_query_filters_by_decision_type(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="adaptation_verdict", source="a",
             athlete_state=sample_state, payload={})
    w.record(decision_type="consensus_verdict", source="b",
             athlete_state=sample_state, payload={})
    w.record(decision_type="adaptation_verdict", source="c",
             athlete_state=sample_state, payload={})

    r = LedgerReader(ledger_path)
    got = r.query(decision_type="adaptation_verdict")
    assert len(got) == 2
    assert all(e.decision_type == "adaptation_verdict" for e in got)


def test_query_filters_by_time_window(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    import time
    w.record(decision_type="phase_transition", source="x",
             athlete_state=sample_state, payload={"n": 1})
    time.sleep(0.005)
    middle_time = datetime.now(timezone.utc)
    time.sleep(0.005)
    w.record(decision_type="phase_transition", source="x",
             athlete_state=sample_state, payload={"n": 2})

    r = LedgerReader(ledger_path)
    after_middle = r.query(since=middle_time)
    assert len(after_middle) == 1
    assert after_middle[0].payload["n"] == 2


def test_query_limit_takes_most_recent(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    for i in range(10):
        w.record(decision_type="adaptation_verdict", source="x",
                 athlete_state=sample_state, payload={"i": i})

    r = LedgerReader(ledger_path)
    last3 = r.query(limit=3)
    assert len(last3) == 3
    assert [e.payload["i"] for e in last3] == [7, 8, 9]


# ---------- query_similar ----------

def test_query_similar_matches_phase_and_ctl(ledger_path):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=72.0, phase="BUILD"), payload={"tag": "match_A"})
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=73.8, phase="BUILD"), payload={"tag": "match_B"})
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=85.0, phase="BUILD"), payload={"tag": "too_far"})
    w.record(decision_type="weekly_plan_assembled", source="t",
             athlete_state=_state(ctl=72.5, phase="PEAK"), payload={"tag": "wrong_phase"})

    r = LedgerReader(ledger_path)
    query_state = _state(ctl=72.0, phase="BUILD")
    hits = r.query_similar(
        athlete_state=query_state,
        decision_type="weekly_plan_assembled",
        ctl_tolerance=5.0,
        phase_match=True,
        limit=5,
    )
    tags = {e.payload["tag"] for e in hits}
    assert tags == {"match_A", "match_B"}


def test_query_similar_phase_match_false_allows_any_phase(ledger_path):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="consensus_verdict", source="t",
             athlete_state=_state(ctl=72.0, phase="BUILD"), payload={"tag": "build"})
    w.record(decision_type="consensus_verdict", source="t",
             athlete_state=_state(ctl=72.5, phase="PEAK"), payload={"tag": "peak"})

    r = LedgerReader(ledger_path)
    hits = r.query_similar(
        athlete_state=_state(ctl=72.0, phase="BUILD"),
        decision_type="consensus_verdict",
        ctl_tolerance=5.0, phase_match=False, limit=5,
    )
    assert {e.payload["tag"] for e in hits} == {"build", "peak"}


def test_query_similar_returns_most_recent_first(ledger_path):
    w = LedgerWriter(ledger_path)
    for i in range(10):
        w.record(decision_type="weekly_plan_assembled", source="t",
                 athlete_state=_state(ctl=72.0, phase="BUILD"), payload={"i": i})

    r = LedgerReader(ledger_path)
    hits = r.query_similar(
        athlete_state=_state(ctl=72.0, phase="BUILD"),
        decision_type="weekly_plan_assembled",
        ctl_tolerance=5.0, phase_match=True, limit=3,
    )
    assert [e.payload["i"] for e in hits] == [9, 8, 7]


# ---------- trace_chain ----------

def test_trace_chain_follows_superseded_by(ledger_path, sample_state):
    """Correction chain: c corrects b; b stands on its own; trace from c yields [c, b]."""
    w = LedgerWriter(ledger_path)
    id_b = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": "original"})
    id_c = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": "corrected"},
                    superseded_by=id_b)

    r = LedgerReader(ledger_path)
    chain = r.trace_chain(id_c)
    assert [e.entry_id for e in chain] == [id_c, id_b]


def test_trace_chain_unknown_entry_returns_empty(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="phase_transition", source="t",
             athlete_state=sample_state, payload={})
    r = LedgerReader(ledger_path)
    assert r.trace_chain("01ZZZZZZZZZZZZZZZZZZZZZZZZ") == []


def test_trace_chain_detects_cycle(ledger_path, sample_state):
    """Fabricated cycle must not hang trace_chain (bounded visit)."""
    w = LedgerWriter(ledger_path)
    id_a = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": 1})
    id_b = w.record(decision_type="phase_transition", source="t",
                    athlete_state=sample_state, payload={"n": 2},
                    superseded_by=id_a)
    from pathlib import Path as _P
    import json as _json
    from datetime import datetime as _dt, timezone as _tz
    cycled = {
        "schema_version": 1,
        "entry_id": id_a,
        "timestamp": _dt.now(_tz.utc).isoformat(),
        "decision_type": "phase_transition",
        "source": "t",
        "athlete_state_ref": sample_state.model_dump(),
        "confidence": None,
        "payload": {"n": "cycled"},
        "evidence_refs": [],
        "superseded_by": id_b,
    }
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(_json.dumps(cycled) + "\n")

    r = LedgerReader(ledger_path)
    chain = r.trace_chain(id_a)
    assert 1 <= len(chain) <= 3


# ---------- Corruption tolerance ----------

def test_query_skips_corrupt_lines(tmp_path, sample_state):
    p = tmp_path / "decisions.jsonl"
    w = LedgerWriter(p)
    w.record(decision_type="adaptation_verdict", source="t",
             athlete_state=sample_state, payload={"ok": 1})
    with open(p, "a", encoding="utf-8") as f:
        f.write("NOT_JSON_AT_ALL\n")
    w.record(decision_type="adaptation_verdict", source="t",
             athlete_state=sample_state, payload={"ok": 2})

    r = LedgerReader(p)
    entries = r.query()
    assert len(entries) == 2
    assert [e.payload["ok"] for e in entries] == [1, 2]
