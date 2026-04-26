"""Human-gated ICU PUT after adapter daily verdict.

Default: dry-run — print the payload that would be sent, exit 0.
With --confirm: send PUT /athlete/{id}/events/{event_id} via ICUClient.update_event,
then append `adaptation_applied` to ledger.

Transactional invariant: ledger entry is appended ONLY after PUT succeeds.
On any PUT exception, the ledger stays untouched and the exception propagates.
"""
from __future__ import annotations

import json
from datetime import date as DateT
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import DecisionEntry
from src.coach.ledger.writer import LedgerWriter
from src.coach.session_designer.types import DesignedSession
from src.fetcher.icu_client import ICUClient

_log = get_logger("adapter")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _find_today_verdict(reader: LedgerReader, target_date: DateT) -> DecisionEntry:
    """Resolve today's adaptation_verdict — fail fast if no same-day entry exists.

    Filters strictly by the target UTC day. A stale-verdict fallback would
    silently apply yesterday's verdict to today's session, which is a safety
    failure. Tests that need a same-day verdict must construct one via injected
    `now_fn` and same-day ledger entries.
    """
    day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    day_end = day_start.replace(hour=23, minute=59, second=59)
    same_day = reader.query(
        decision_type="adaptation_verdict",
        since=day_start, until=day_end,
    )
    if not same_day:
        raise ValueError(
            f"No adaptation_verdict found for {target_date.isoformat()}")
    return same_day[-1]


def _find_today_event_id(warehouse_dir: Path, target_date: DateT) -> str:
    events = _read_json(warehouse_dir / "8_Events" / "events.json")
    if not isinstance(events, list):
        raise FileNotFoundError(
            f"events.json missing or malformed in {warehouse_dir}/8_Events")
    iso = target_date.isoformat()
    candidates = [
        e for e in events
        if isinstance(e.get("start_date_local"), str)
        and e["start_date_local"].startswith(iso)
        and e.get("category") in ("WORKOUT", "NOTE")
    ]
    if not candidates:
        raise FileNotFoundError(f"No ICU event for {iso}; cannot apply")
    candidates.sort(key=lambda e: str(e.get("id", "")))
    return str(candidates[-1]["id"])


def _build_patch_payload(
    proposed: DesignedSession | None, verdict_payload: dict[str, Any],
) -> dict[str, Any]:
    if proposed is None:
        # Rest path
        triggered = verdict_payload.get("triggered_rules") or []
        if triggered:
            description = (
                f"Adapter flagged {verdict_payload.get('verdict', 'red').upper()}: "
                f"{', '.join(triggered)}"
            )
        else:
            description = "Rest day (auto from adapter)"
        return {
            "name": "Rest day (auto, adapter)",
            "description": description,
            "category": "NOTE",
            "moving_time": 0,
            "icu_training_load": 0,
        }
    return {
        "name": proposed.name,
        "description": proposed.description,
        "category": "WORKOUT",
        "moving_time": int(proposed.duration_min) * 60,
        "icu_training_load": int(proposed.target_tss),
    }


def run(
    *,
    target_date: DateT,
    memory_dir: Path,
    warehouse_dir: Path,
    client_factory: Callable[[], Any] | None = None,
    writer: LedgerWriter | None = None,
    reader: LedgerReader | None = None,
    now_fn: Callable[[], datetime] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Resolve today's verdict + ICU event, build PUT payload, optionally apply.

    Returns dict with keys:
      mode: "dry_run" | "applied"
      event_id: str
      patch_payload: dict   (the body that would be / was sent)
      ledger_entry_id: str | None (None unless confirm=True AND PUT succeeded)
      verdict_entry_id: str  (the source adaptation_verdict ULID)
      applied_at: datetime  (timestamp from now_fn() at the time of this run;
                             surfaced in both dry_run and applied paths)

    Raises if PUT fails under confirm=True (ledger then NOT appended).
    """
    if now_fn is None:
        now_fn = lambda: datetime.now(timezone.utc)
    applied_at = now_fn()
    if client_factory is None:
        client_factory = lambda: ICUClient()
    if reader is None:
        reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    if writer is None:
        writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")

    verdict_entry = _find_today_verdict(reader, target_date)
    if verdict_entry.payload.get("verdict") != "red":
        raise ValueError(
            f"Today's verdict is {verdict_entry.payload.get('verdict')!r}; "
            "only 'red' verdicts can be applied to ICU.")

    proposed_path = memory_dir / "adapter" / f"proposed_session_{target_date.isoformat()}.json"
    proposed: DesignedSession | None = None
    if proposed_path.exists():
        proposed = DesignedSession.model_validate_json(
            proposed_path.read_text(encoding="utf-8"))

    event_id = _find_today_event_id(warehouse_dir, target_date)
    payload = _build_patch_payload(proposed, verdict_entry.payload)

    if not confirm:
        _log.event(
            "apply_dry_run",
            date=target_date.isoformat(),
            event_id=event_id,
            recommended_action=verdict_entry.payload.get("recommended_action"),
        )
        return {
            "mode": "dry_run",
            "event_id": event_id,
            "patch_payload": payload,
            "ledger_entry_id": None,
            "verdict_entry_id": verdict_entry.entry_id,
            "applied_at": applied_at,
        }

    client = client_factory()
    try:
        client.update_event(event_id, payload)
    except Exception as exc:
        _log.event(
            "apply_failed",
            date=target_date.isoformat(),
            event_id=event_id,
            status="error",
            error=str(exc),
            recommended_action="abort_no_ledger",
        )
        raise

    # PUT succeeded — ONLY NOW append ledger
    entry_id = writer.record(
        decision_type="adaptation_applied",
        source="adapter.apply",
        athlete_state=verdict_entry.athlete_state_ref,
        payload={
            "event_id": event_id,
            "source_verdict_entry_id": verdict_entry.entry_id,
            "patched_fields": list(payload.keys()),
            "verdict": verdict_entry.payload.get("verdict"),
            "recommended_action": verdict_entry.payload.get("recommended_action"),
        },
        evidence_refs=[verdict_entry.entry_id],
        confidence=1.0,
    )
    _log.event(
        "adaptation_applied",
        date=target_date.isoformat(),
        event_id=event_id,
        recommended_action=verdict_entry.payload.get("recommended_action"),
    )
    return {
        "mode": "applied",
        "event_id": event_id,
        "patch_payload": payload,
        "ledger_entry_id": entry_id,
        "verdict_entry_id": verdict_entry.entry_id,
        "applied_at": applied_at,
    }
