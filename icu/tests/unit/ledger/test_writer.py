"""Unit tests for LedgerWriter: atomic append, concurrent-safe, schema-strict."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path

import pytest

from src.coach.ledger.types import AthleteStateRef, is_valid_ulid
from src.coach.ledger.writer import LedgerWriter


def test_record_creates_file_and_appends_line(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    entry_id = w.record(
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state=sample_state,
        payload={"verdict": "green"},
        confidence=1.0,
    )
    assert is_valid_ulid(entry_id)
    lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    doc = json.loads(lines[0])
    assert doc["entry_id"] == entry_id
    assert doc["decision_type"] == "adaptation_verdict"
    assert doc["payload"] == {"verdict": "green"}


def test_record_appends_without_rewriting(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    for i in range(5):
        w.record(
            decision_type="phase_transition",
            source="test",
            athlete_state=sample_state,
            payload={"seq": i},
        )
    lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    payloads = [json.loads(l)["payload"]["seq"] for l in lines]
    assert payloads == [0, 1, 2, 3, 4]


def test_record_returns_distinct_ulids(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    ids = [
        w.record(decision_type="consensus_verdict", source="test",
                 athlete_state=sample_state, payload={"i": i})
        for i in range(100)
    ]
    assert len(set(ids)) == 100


def test_record_evidence_refs_default_empty(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(decision_type="micro_cycle_generated", source="test",
             athlete_state=sample_state, payload={})
    doc = json.loads(Path(ledger_path).read_text().splitlines()[0])
    assert doc["evidence_refs"] == []
    assert doc["superseded_by"] is None


def test_record_persists_optional_fields(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    w.record(
        decision_type="weekly_plan_assembled",
        source="ingester",
        athlete_state=sample_state,
        payload={"total_tss": 480},
        evidence_refs=["reports/plan_20260419.trace.json"],
        confidence=0.82,
    )
    doc = json.loads(Path(ledger_path).read_text().splitlines()[0])
    assert doc["evidence_refs"] == ["reports/plan_20260419.trace.json"]
    assert doc["confidence"] == 0.82


def test_record_rejects_invalid_decision_type(ledger_path, sample_state):
    w = LedgerWriter(ledger_path)
    with pytest.raises(Exception):
        w.record(decision_type="bogus", source="test",
                 athlete_state=sample_state, payload={})
    if Path(ledger_path).exists():
        assert Path(ledger_path).read_text() == ""


# ---------- Concurrency ----------

def _child_write(path: str, n: int, state_dict: dict):
    """Worker process: write N entries to the shared ledger."""
    from src.coach.ledger.writer import LedgerWriter
    from src.coach.ledger.types import AthleteStateRef
    state = AthleteStateRef(**state_dict)
    w = LedgerWriter(Path(path))
    for i in range(n):
        w.record(decision_type="adaptation_verdict", source=f"proc.{os.getpid()}",
                 athlete_state=state, payload={"i": i, "pid": os.getpid()})


def test_concurrent_writes_produce_valid_lines(ledger_path, sample_state):
    """Two processes each write 50 entries; total must be 100 valid lines."""
    state_dict = sample_state.model_dump()
    procs = [mp.Process(target=_child_write, args=(str(ledger_path), 50, state_dict))
             for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0

    lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
    for line in lines:
        doc = json.loads(line)
        assert is_valid_ulid(doc["entry_id"])
        assert doc["decision_type"] == "adaptation_verdict"


def test_append_mode_tolerates_corrupt_trailing_line(tmp_path, sample_state):
    """Pre-existing file with a half-written last line: new record still appends."""
    p = tmp_path / "decisions.jsonl"
    p.write_text('{"entry_id": "01HF0", "decision_type":', encoding="utf-8")
    w = LedgerWriter(p)
    w.record(decision_type="phase_transition", source="test",
             athlete_state=sample_state, payload={"ok": True})
    text = p.read_text(encoding="utf-8")
    assert text.count("\n") >= 1
    last_line = text.splitlines()[-1]
    doc = json.loads(last_line)
    assert doc["payload"] == {"ok": True}
