"""T69.1 RED — action_suggester pure function + 4 trigger detectors."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


def _write_ledger_entry(path: Path, *, decision_type: str, ts: datetime,
                        payload: dict, entry_id: str = "01HABCDEF0123456789ABCDEFG",
                        source: str = "test") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {"ctl": 60.0, "atl": 65.0, "tsb": -5.0, "w_prime": 18000,
             "phase": "BUILD", "week_of_year": 17}
    rec = {
        "schema_version": 1,
        "entry_id": entry_id,
        "timestamp": ts.isoformat(),
        "decision_type": decision_type,
        "source": source,
        "athlete_state_ref": state,
        "confidence": None,
        "payload": payload,
        "evidence_refs": [],
        "superseded_by": None,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _ulid(n: int) -> str:
    """Stable monotonic-ish ULID-like 26-char string for tests."""
    return f"01HABCDEF0123456789ABCDE{n:02d}"


@pytest.fixture
def empty_dirs(tmp_path: Path) -> dict[str, Path]:
    return {
        "ledger": tmp_path / "ledger" / "decisions.jsonl",
        "periodization": tmp_path / "periodization",
        "deep_analysis": tmp_path / "deep_analysis",
    }


def test_no_triggers_returns_empty_list(empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    # Deviation: trigger 3 (consensus_overdue) fires when no consensus exists
    # per spec L306-308. Seed a recent consensus_verdict so all triggers stay
    # silent — required to test the truly-empty-output path.
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(0))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert out == []


def test_trigger1_phase_transition_within_7_days_fires(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=2),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="phase_transition", ts=ts,
                        payload={"new_phase": "PEAK"}, entry_id=_ulid(1))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("阶段切换" in line for line in out)


def test_trigger1_phase_transition_older_than_7_days_silent(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=20),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="phase_transition", ts=ts,
                        payload={"new_phase": "PEAK"}, entry_id=_ulid(2))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    # Trigger 3 (consensus_overdue) DOES fire because no consensus_verdict
    # was ever recorded — so the list is non-empty, but it should NOT
    # contain the phase-transition line.
    assert not any("阶段切换" in line for line in out)


def test_trigger2_safety_violation_in_latest_plan_fires(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=1),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="weekly_plan_assembled", ts=ts,
                        payload={"violations": ["LOAD_SPIKE", "BACK_TO_BACK_HARD"]},
                        entry_id=_ulid(3))
    # Plus a recent consensus to silence trigger 3
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(4))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("safety guard violation" in line for line in out)


def test_trigger2_silent_when_violations_empty(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=1),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="weekly_plan_assembled", ts=ts,
                        payload={"violations": []}, entry_id=_ulid(5))
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(6))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("safety guard violation" in line for line in out)


def test_trigger3_consensus_overdue_when_never_run(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("consensus_verdict" in line and "14 天" in line for line in out)


def test_trigger3_consensus_overdue_after_14d(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=20),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict", ts=ts,
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(7))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("14 天" in line for line in out)


def test_trigger3_consensus_recent_silent(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    ts = datetime.combine(today - timedelta(days=3),
                          datetime.min.time(), tzinfo=timezone.utc)
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict", ts=ts,
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(8))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("14 天" in line for line in out)


def test_trigger4_stimulus_decline_fires(empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    # 3 dated summaries, monotonic decline (older → newer)
    (da / "summary_2026-04-21.json").write_text(
        json.dumps({"stimulus_score": 0.80}), encoding="utf-8")
    (da / "summary_2026-04-22.json").write_text(
        json.dumps({"stimulus_score": 0.50}), encoding="utf-8")
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    # Quiet trigger 3 with a recent consensus
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(9))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert any("stimulus_score 单调下滑" in line for line in out)


def test_trigger4_silent_when_increasing(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    (da / "summary_2026-04-21.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    (da / "summary_2026-04-22.json").write_text(
        json.dumps({"stimulus_score": 0.50}), encoding="utf-8")
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.70}), encoding="utf-8")
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(10))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("stimulus_score" in line for line in out)


def test_trigger4_silent_when_fewer_than_3_summaries(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(11))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("stimulus_score" in line for line in out)


def test_trigger4_skips_summary_latest_json(
        empty_dirs: dict[str, Path]) -> None:
    """summary_latest.json must NOT participate in the 3-window."""
    from src.coach.common.action_suggester import suggest_actions
    today = date(2026, 4, 28)
    da = empty_dirs["deep_analysis"]
    da.mkdir(parents=True, exist_ok=True)
    (da / "summary_2026-04-23.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    (da / "summary_latest.json").write_text(
        json.dumps({"stimulus_score": 0.30}), encoding="utf-8")
    _write_ledger_entry(empty_dirs["ledger"],
                        decision_type="consensus_verdict",
                        ts=datetime.combine(today - timedelta(days=2),
                                            datetime.min.time(),
                                            tzinfo=timezone.utc),
                        payload={"verdict": "ACCEPT"}, entry_id=_ulid(12))
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=today)
    assert not any("stimulus_score" in line for line in out)


def test_today_defaults_to_date_today_when_none(
        empty_dirs: dict[str, Path]) -> None:
    """today=None → uses date.today() at call time, not import time."""
    from src.coach.common.action_suggester import suggest_actions
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=None)
    assert isinstance(out, list)
    assert all(isinstance(line, str) for line in out)


def test_returns_plain_list_str_no_pydantic(
        empty_dirs: dict[str, Path]) -> None:
    from src.coach.common.action_suggester import suggest_actions
    out = suggest_actions(empty_dirs["ledger"], empty_dirs["periodization"],
                          empty_dirs["deep_analysis"], today=date(2026, 4, 28))
    assert type(out) is list


def test_print_suggestions_silent_on_empty(capsys) -> None:
    from src.coach.common.action_suggester import print_suggestions
    print_suggestions([], header="📌 Phase 3 建议")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_suggestions_renders_header_and_bullets(capsys) -> None:
    from src.coach.common.action_suggester import print_suggestions
    print_suggestions(["第一条建议", "第二条建议"], header="📌 Phase 3 建议")
    captured = capsys.readouterr()
    assert "📌 Phase 3 建议" in captured.out
    assert "  • 第一条建议" in captured.out
    assert "  • 第二条建议" in captured.out
