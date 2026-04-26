"""Unit tests for adapter.apply_adaptation.run — dry-run vs --confirm; ledger transactional."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.coach.adapter.apply_adaptation import run as run_apply
from src.coach.adapter.daily_adapt import run as run_daily
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter


# ---------- Build a red-verdict day end-to-end via daily_adapt ----------

@pytest.fixture
def target_date() -> date:
    # LedgerWriter.record stamps with the real wall clock (T58 invariant);
    # the apply_adaptation same-day verdict filter then requires the target
    # date to match today, otherwise no-fallback would (correctly) raise.
    return datetime.now(timezone.utc).date()


@pytest.fixture
def fixed_now(target_date) -> datetime:
    return datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc).replace(hour=6)


@pytest.fixture
def now_fn(fixed_now):
    return lambda: fixed_now


@pytest.fixture
def red_world(tmp_path, target_date, now_fn) -> dict:
    """Set up memory_dir + warehouse_dir with a RED day already evaluated by daily_adapt."""
    memory_dir = tmp_path / "coach_memory"
    warehouse_dir = tmp_path / "icu_data_warehouse"

    (memory_dir / "physiology").mkdir(parents=True)
    (memory_dir / "periodization").mkdir(parents=True)
    (memory_dir / "reports").mkdir(parents=True)
    (memory_dir / "ledger").mkdir(parents=True)
    (warehouse_dir / "2_Wellness").mkdir(parents=True)
    (warehouse_dir / "8_Events").mkdir(parents=True)

    (memory_dir / "physiology" / "cp_w_current.json").write_text(json.dumps({
        "cp_watts": 288, "w_prime_joules": 20000, "athlete_ftp_set": 288,
    }), encoding="utf-8")
    (memory_dir / "physiology" / "durability.json").write_text(json.dumps({
        "decay_rate_pct_per_1000kj": {"60s": 1.5, "300s": 2.1},
        "sample_size_rides": 28,
    }), encoding="utf-8")
    (memory_dir / "physiology" / "response_profile.json").write_text(json.dumps({
        "types": {}}), encoding="utf-8")
    (memory_dir / "periodization" / "phase_current.json").write_text(json.dumps({
        "current_phase": "BUILD"}), encoding="utf-8")

    # 28d baseline + red target day
    history = [
        {"id": f"{(target_date - timedelta(days=i)).isoformat()}T00:00:00",
         "hrv": 68.0, "restingHR": 52, "sleepSecs": 7 * 3600,
         "soreness": 4, "ctl": 70.0, "atl": 75.0}
        for i in range(30, 0, -1)
    ] + [{
        "id": f"{target_date.isoformat()}T00:00:00",
        "hrv": 68.0 * 0.80, "restingHR": 60, "sleepSecs": 3 * 3600,
        "soreness": 1, "ctl": 70.0, "atl": 80.0,
    }]
    (warehouse_dir / "2_Wellness" / "wellness_history.json").write_text(
        json.dumps(history), encoding="utf-8")

    # plan with a Threshold session today
    plan = {
        "week_start": target_date.isoformat(),
        "week_end": (target_date + timedelta(days=6)).isoformat(),
        "focus_theme": "test",
        "weekly_tss_target": 400,
        "coaching_summary": None,
        "days": [{
            "date": target_date.isoformat(),
            "day_of_week": target_date.strftime("%a"),
            "training_type": "Threshold",
            "icu_type": "Ride",
            "name": "Threshold 2x20",
            "description": "2x20 @ FTP",
            "duration_min": 90,
            "target_tss": 110,
            "power_range_w": "260-280", "hr_range_bpm": "150-165",
        }],
    }
    (memory_dir / "reports" / f"plan_{target_date.isoformat()}.json").write_text(
        json.dumps(plan), encoding="utf-8")

    # ICU events.json (today's WORKOUT event)
    events = [{
        "id": "evt_999",
        "start_date_local": f"{target_date.isoformat()}T07:00:00",
        "category": "WORKOUT",
        "name": "Threshold 2x20",
    }]
    (warehouse_dir / "8_Events" / "events.json").write_text(
        json.dumps(events), encoding="utf-8")

    # Drive daily_adapt to write today_<date>.md, proposed_session_<date>.json,
    # and the ledger adaptation_verdict entry.
    ledger_path = memory_dir / "ledger" / "decisions.jsonl"
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)
    daily_result = run_daily(
        target_date=target_date,
        memory_dir=memory_dir, warehouse_dir=warehouse_dir,
        writer=writer, reader=reader, now_fn=now_fn,
    )
    assert daily_result["verdict"] == "red"
    assert daily_result["proposed_session_path"] is not None

    return {
        "memory_dir": memory_dir,
        "warehouse_dir": warehouse_dir,
        "ledger_path": ledger_path,
    }


# ---------- DRY-RUN: payload printed, no fetcher call, no ledger ----------

def test_dry_run_does_not_call_client_or_ledger(red_world, target_date, now_fn):
    mock_client = MagicMock()
    writer = LedgerWriter(red_world["ledger_path"])
    reader = LedgerReader(red_world["ledger_path"])
    n_before = len(reader.query(decision_type="adaptation_applied"))

    result = run_apply(
        target_date=target_date,
        memory_dir=red_world["memory_dir"],
        warehouse_dir=red_world["warehouse_dir"],
        client_factory=lambda: mock_client,
        writer=writer, reader=reader, now_fn=now_fn,
        confirm=False,
    )
    assert result["mode"] == "dry_run"
    assert result["event_id"] == "evt_999"
    assert result["ledger_entry_id"] is None
    assert isinstance(result["patch_payload"], dict)
    assert "name" in result["patch_payload"]

    mock_client.update_event.assert_not_called()
    n_after = len(reader.query(decision_type="adaptation_applied"))
    assert n_before == n_after  # NO ledger row added


# ---------- --confirm happy: client called, ledger appended ----------

def test_confirm_happy_path_calls_client_and_appends_ledger(
    red_world, target_date, now_fn,
):
    mock_client = MagicMock()
    mock_client.update_event.return_value = {"id": "evt_999"}
    writer = LedgerWriter(red_world["ledger_path"])
    reader = LedgerReader(red_world["ledger_path"])
    n_before = len(reader.query(decision_type="adaptation_applied"))

    result = run_apply(
        target_date=target_date,
        memory_dir=red_world["memory_dir"],
        warehouse_dir=red_world["warehouse_dir"],
        client_factory=lambda: mock_client,
        writer=writer, reader=reader, now_fn=now_fn,
        confirm=True,
    )
    assert result["mode"] == "applied"
    assert result["event_id"] == "evt_999"
    assert result["ledger_entry_id"] is not None

    mock_client.update_event.assert_called_once()
    args, kwargs = mock_client.update_event.call_args
    # First positional = event_id; second positional = payload dict
    assert args[0] == "evt_999"
    payload = args[1] if len(args) > 1 else kwargs.get("event_data") or kwargs.get("payload")
    assert isinstance(payload, dict)
    assert "name" in payload

    applied_entries = reader.query(decision_type="adaptation_applied")
    assert len(applied_entries) == n_before + 1
    last = applied_entries[-1]
    assert last.payload["event_id"] == "evt_999"
    assert "source_verdict_entry_id" in last.payload


# ---------- --confirm failure: NO ledger entry, exception raised ----------

def test_confirm_patch_failure_does_not_write_ledger(
    red_world, target_date, now_fn,
):
    mock_client = MagicMock()

    class _PatchFailed(RuntimeError):
        pass

    mock_client.update_event.side_effect = _PatchFailed("HTTP 503")
    writer = LedgerWriter(red_world["ledger_path"])
    reader = LedgerReader(red_world["ledger_path"])
    n_before = len(reader.query(decision_type="adaptation_applied"))
    size_before = red_world["ledger_path"].stat().st_size

    with pytest.raises(_PatchFailed):
        run_apply(
            target_date=target_date,
            memory_dir=red_world["memory_dir"],
            warehouse_dir=red_world["warehouse_dir"],
            client_factory=lambda: mock_client,
            writer=writer, reader=reader, now_fn=now_fn,
            confirm=True,
        )
    # Ledger uncorrupted: neither parseable count nor raw byte size changed.
    n_after = len(reader.query(decision_type="adaptation_applied"))
    assert n_after == n_before
    assert red_world["ledger_path"].stat().st_size == size_before


# ---------- Missing verdict: fail-fast ----------

def test_no_verdict_today_raises(tmp_path, target_date, now_fn):
    memory_dir = tmp_path / "coach_memory"
    warehouse_dir = tmp_path / "icu_data_warehouse"
    (memory_dir / "ledger").mkdir(parents=True)
    (warehouse_dir / "8_Events").mkdir(parents=True)
    (warehouse_dir / "8_Events" / "events.json").write_text(json.dumps([]), encoding="utf-8")
    writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")
    reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    with pytest.raises((ValueError, FileNotFoundError)):
        run_apply(
            target_date=target_date,
            memory_dir=memory_dir, warehouse_dir=warehouse_dir,
            client_factory=lambda: MagicMock(),
            writer=writer, reader=reader, now_fn=now_fn,
            confirm=False,
        )


# ---------- Yellow / green verdict cannot be applied ----------

def test_yellow_verdict_refuses_apply(red_world, target_date, now_fn):
    """Manually overwrite ledger to put a YELLOW entry today, then try to apply -> ValueError."""
    # Swap the ledger to a single yellow entry
    ledger_path = red_world["ledger_path"]
    ledger_path.write_text("", encoding="utf-8")
    writer = LedgerWriter(ledger_path)
    reader = LedgerReader(ledger_path)
    writer.record(
        decision_type="adaptation_verdict",
        source="adapter.daily",
        athlete_state=AthleteStateRef(
            ctl=70.0, atl=75.0, tsb=-5.0,
            w_prime=20000, phase="BUILD",
            week_of_year=target_date.isocalendar()[1],
        ),
        payload={
            "verdict": "yellow",
            "severity_score": 0.4,
            "recommended_action": "nudge_only",
            "triggered_rules": [],
            "guardrails_hit": [],
            "original_session_type": "THRESHOLD",
            "proposed_session_type": None,
            "report_path": None,
            "proposed_session_path": None,
        },
    )
    with pytest.raises(ValueError):
        run_apply(
            target_date=target_date,
            memory_dir=red_world["memory_dir"],
            warehouse_dir=red_world["warehouse_dir"],
            client_factory=lambda: MagicMock(),
            writer=writer, reader=reader, now_fn=now_fn,
            confirm=False,
        )


# ---------- Defense-in-depth: no LLM SDK transitive import ----------

def test_module_does_not_import_llm_sdks():
    import sys
    forbidden = ("google.genai", "anthropic", "openai")
    # Importing the module under test must not pull in any LLM SDK
    from src.coach.adapter import apply_adaptation  # noqa: F401
    for name in forbidden:
        assert name not in sys.modules, f"forbidden import: {name}"


# ---------- ICUClient extension exists ----------

def test_icu_client_has_update_event_method():
    from src.fetcher.icu_client import ICUClient
    assert hasattr(ICUClient, "update_event"), \
        "T61 must add ICUClient.update_event(event_id, event_data)"


# ---------- now_fn injection seam ----------

def test_now_fn_is_used_not_real_clock(red_world, target_date, fixed_now):
    """The injected `now_fn` must populate `applied_at` on the result dict —
    proves the injection seam exists and isn't shadowed by real wall clock."""
    mock_client = MagicMock()
    mock_client.update_event.return_value = {"id": "evt_999"}
    writer = LedgerWriter(red_world["ledger_path"])
    reader = LedgerReader(red_world["ledger_path"])

    result = run_apply(
        target_date=target_date,
        memory_dir=red_world["memory_dir"],
        warehouse_dir=red_world["warehouse_dir"],
        client_factory=lambda: mock_client,
        writer=writer, reader=reader,
        now_fn=lambda: fixed_now,
        confirm=False,
    )
    assert result["applied_at"] == fixed_now
