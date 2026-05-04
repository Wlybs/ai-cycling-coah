"""Daily adaptation orchestrator — pure function, no IO except via injected writer.

Composes:
  wellness + plan + physiology + ledger history
    -> SignalSnapshot + AthleteStateRef
    -> evaluate_signals  -> AdaptationVerdict
    -> (red) revise_session -> DesignedSession | None
    -> build_yellow_nudge / build_red_override -> markdown
    -> write report + proposed_session + ledger entry  (skipped under dry_run)

CLI is a thin shell in scripts/daily_adapt.py.
"""
from __future__ import annotations

import json
import logging
from datetime import date as DateT
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from src.coach.common.logging import get_logger
from src.coach.ledger.reader import LedgerReader
from src.coach.ledger.types import AthleteStateRef
from src.coach.ledger.writer import LedgerWriter
from src.coach.periodization.types import SessionType
from src.coach.session_designer.types import (
    DayPlanV2,
    DesignedSession,
    SessionStructure,
    WeeklyPlan,
)

from .prompt_builder import build_red_override, build_yellow_nudge
from .rules import evaluate_signals
from .session_revisor import revise_session
from .types import SignalSnapshot

_log = get_logger("adapter")
logger = logging.getLogger(__name__)

# Phase 2 DayPlanV2.training_type -> SessionType
_TRAINING_TYPE_TO_SESSION_TYPE: dict[str, SessionType] = {
    "Rest":          SessionType.REST,
    "Recovery":      SessionType.RECOVERY,
    "Aerobic":       SessionType.AEROBIC,
    "Tempo":         SessionType.TEMPO,
    "Threshold":     SessionType.THRESHOLD,
    "VO2max":        SessionType.VO2MAX,
    "Neuromuscular": SessionType.NEUROMUSCULAR,
    "Race":          SessionType.RACE,
}

_BASELINE_DAYS = 28
_BASELINE_MIN_SAMPLES = 7  # below this, return None -> evaluate_signals skips that signal


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {path}: {e}") from e


def _wellness_for_date(history: list[dict], target_date: DateT) -> dict:
    iso = target_date.isoformat()
    for entry in history:
        if isinstance(entry.get("id"), str) and entry["id"].startswith(iso):
            return entry
    raise ValueError(f"No wellness entry for {iso} in history")


def _baseline_window(history: list[dict], target_date: DateT, key: str) -> float | None:
    iso_cutoff = target_date.isoformat()
    samples: list[float] = []
    for entry in history:
        eid = entry.get("id", "")
        if not isinstance(eid, str) or len(eid) < 10:
            continue
        d = eid[:10]
        if d >= iso_cutoff:
            continue
        # Within the prior _BASELINE_DAYS window?
        if d < (target_date - timedelta(days=_BASELINE_DAYS)).isoformat():
            continue
        v = entry.get(key)
        if isinstance(v, (int, float)):
            samples.append(float(v))
    if len(samples) < _BASELINE_MIN_SAMPLES:
        return None
    return sum(samples) / len(samples)


def _build_signal_snapshot(
    history: list[dict], target_date: DateT, now: datetime,
) -> SignalSnapshot:
    today = _wellness_for_date(history, target_date)
    sleep_secs = today.get("sleepSecs")
    if sleep_secs is None:
        raise ValueError(f"sleepSecs missing for {target_date.isoformat()}")
    return SignalSnapshot(
        captured_at=now,
        hrv_ms=float(today["hrv"]) if today.get("hrv") is not None else 0.0,
        resting_hr_bpm=int(today["restingHR"]) if today.get("restingHR") is not None else 0,
        sleep_hours=float(sleep_secs) / 3600.0,
        soreness_score=int(today["soreness"]) if today.get("soreness") is not None else None,
    )


# DRIFT: keep field set in sync with scripts.ingest_ledger._FALLBACK_STATE
def _fallback_state(target_date: DateT) -> AthleteStateRef:
    """Conservative fallback when warehouse / physiology snapshots are absent.

    Mirrors scripts.ingest_ledger._FALLBACK_STATE shape (phase='UNKNOWN', zeroed
    load metrics) but pegs week_of_year to target_date instead of today's wall
    clock — keeps `--date` driven runs deterministic across re-runs.
    """
    return AthleteStateRef(
        ctl=0.0, atl=0.0, tsb=0.0, w_prime=0,
        phase="UNKNOWN", week_of_year=target_date.isocalendar()[1],
    )


def _build_athlete_state(
    memory_dir: Path, warehouse_dir: Path, target_date: DateT,
) -> AthleteStateRef:
    wellness = _read_json(warehouse_dir / "2_Wellness" / "wellness_history.json")
    cp_w = _read_json(memory_dir / "physiology" / "cp_w_current.json")
    phase_doc = _read_json(memory_dir / "periodization" / "phase_current.json")

    if not isinstance(wellness, list) or not wellness:
        return _fallback_state(target_date)

    latest = wellness[-1]
    ctl = latest.get("ctl")
    atl = latest.get("atl")
    if ctl is None or atl is None:
        return _fallback_state(target_date)

    w_prime = (cp_w or {}).get("w_prime_joules", 0)
    phase = (phase_doc or {}).get("current_phase", "UNKNOWN")

    try:
        return AthleteStateRef(
            ctl=float(ctl),
            atl=float(atl),
            tsb=float(ctl) - float(atl),
            w_prime=int(w_prime),
            phase=str(phase),
            week_of_year=target_date.isocalendar()[1],
        )
    except (ValueError, TypeError, ValidationError) as exc:
        logger.warning(
            "Failed to build AthleteStateRef from %s, falling back: %s",
            memory_dir / "physiology" / "cp_w_current.json", exc,
            exc_info=False,
        )
        return _fallback_state(target_date)


def _day_to_designed_session(day: DayPlanV2) -> DesignedSession:
    s_type = _TRAINING_TYPE_TO_SESSION_TYPE.get(day.training_type, SessionType.AEROBIC)
    return DesignedSession(
        day_of_week=day.day_of_week,
        date=day.date,
        session_type=s_type,
        name=day.name,
        description=day.description,
        duration_min=day.duration_min,
        target_tss=day.target_tss,
        structure=SessionStructure(steps=[]),
        power_range_w=day.power_range_w,
        hr_range_bpm=day.hr_range_bpm,
        trace=None,
    )


def _find_original_session(
    memory_dir: Path, target_date: DateT,
) -> DesignedSession | None:
    rep_dir = memory_dir / "reports"
    if not rep_dir.exists():
        return None
    candidates = [p for p in rep_dir.glob("plan_*.json")
                  if not p.name.endswith(".trace.json")]
    if not candidates:
        return None
    # Newest by mtime (plan filenames are inconsistent: date vs ISO-week)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            plan = WeeklyPlan.model_validate_json(
                path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("Skipped plan candidate %s: %s", path, exc)
            continue
        for day in plan.days:
            if day.date == target_date.isoformat():
                return _day_to_designed_session(day)
    return None


def run(
    *,
    target_date: DateT,
    memory_dir: Path,
    warehouse_dir: Path,
    writer: LedgerWriter | None = None,
    reader: LedgerReader | None = None,
    now_fn: Callable[[], datetime] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Evaluate today's signals; (optionally) persist outputs; return result dict.

    Returns a dict with keys:
      verdict: "green" | "yellow" | "red"
      severity_score: float
      recommended_action: str
      triggered_rules: list[str]
      guardrails_hit: list[str]
      report_path: Path | None       (None for green / dry_run)
      proposed_session_path: Path | None
      ledger_entry_id: str | None    (None when dry_run)
      captured_at: datetime          (snapshot timestamp, derived from now_fn)

    Pure orchestrator: NO sys.exit, NO argv parse, NO print.
    """
    if now_fn is None:
        now_fn = lambda: datetime.now(timezone.utc)
    now = now_fn()
    wellness_path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    history = _read_json(wellness_path)
    if not isinstance(history, list) or not history:
        raise FileNotFoundError(
            f"wellness_history.json missing or empty: {wellness_path}")

    snapshot = _build_signal_snapshot(history, target_date, now)
    state = _build_athlete_state(memory_dir, warehouse_dir, target_date)
    baseline_hrv = _baseline_window(history, target_date, "hrv")
    baseline_hr = _baseline_window(history, target_date, "restingHR")

    # Read prior adaptation_verdict entries for the consecutive-red guardrail.
    if reader is None:
        reader = LedgerReader(memory_dir / "ledger" / "decisions.jsonl")
    history_entries = reader.query(
        decision_type="adaptation_verdict",
        since=now - timedelta(days=4),
    )

    verdict = evaluate_signals(
        snapshot,
        state=state,
        history=history_entries,
        hrv_28d_mean_ms=baseline_hrv,
        resting_hr_28d_mean_bpm=baseline_hr,
    )

    # Find original session + branch on verdict
    original = _find_original_session(memory_dir, target_date)
    physiology = _read_json(memory_dir / "physiology" / "cp_w_current.json") or {}
    durability = _read_json(memory_dir / "physiology" / "durability.json") or {}
    response_profile = _read_json(
        memory_dir / "physiology" / "response_profile.json") or {}

    report_md: str | None = None
    proposed: DesignedSession | None = None

    if verdict.verdict == "yellow":
        report_md = build_yellow_nudge(
            verdict=verdict, snapshot=snapshot, today_session=original,
        )
    elif verdict.verdict == "red":
        original_type = original.session_type if original is not None else SessionType.REST
        proposed = revise_session(
            original_type=original_type,
            original_date=target_date,
            physiology=physiology,
            durability=durability,
            response_profile=response_profile,
        )
        report_md = build_red_override(
            verdict=verdict, snapshot=snapshot,
            original=original, proposed=proposed,
        )
    # green: report_md stays None, proposed stays None

    # Persist (skip when dry_run)
    report_path: Path | None = None
    proposed_path: Path | None = None
    entry_id: str | None = None

    if not dry_run:
        if report_md is not None:
            report_path = memory_dir / "adapter" / f"today_{target_date.isoformat()}.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_md, encoding="utf-8")
        if proposed is not None:
            proposed_path = (
                memory_dir / "adapter"
                / f"proposed_session_{target_date.isoformat()}.json"
            )
            proposed_path.parent.mkdir(parents=True, exist_ok=True)
            proposed_path.write_text(
                proposed.model_dump_json(indent=2), encoding="utf-8")

        if writer is None:
            writer = LedgerWriter(memory_dir / "ledger" / "decisions.jsonl")

        payload: dict[str, Any] = {
            "verdict": verdict.verdict,
            "severity_score": verdict.severity_score,
            "recommended_action": verdict.recommended_action,
            "triggered_rules": list(verdict.triggered_rules),
            "guardrails_hit": list(verdict.guardrails_hit),
            "original_session_type": original.session_type.value if original else None,
            "proposed_session_type": proposed.session_type.value if proposed else None,
            "report_path": (
                str(report_path.relative_to(memory_dir))
                if report_path else None
            ),
            "proposed_session_path": (
                str(proposed_path.relative_to(memory_dir))
                if proposed_path else None
            ),
        }
        ledger_path = memory_dir / "ledger" / "decisions.jsonl"
        try:
            entry_id = writer.record(
                decision_type="adaptation_verdict",
                source="adapter.daily",
                athlete_state=state,
                payload=payload,
                evidence_refs=[str(wellness_path)],
                confidence=1.0,
            )
        except OSError as exc:
            raise FileNotFoundError(
                f"Ledger write failed at {ledger_path}: {exc}") from exc

    _log.event(
        "adapter_run_completed",
        date=target_date.isoformat(),
        verdict=verdict.verdict,
        recommended_action=verdict.recommended_action,
        dry_run=dry_run,
    )

    return {
        "verdict": verdict.verdict,
        "severity_score": verdict.severity_score,
        "recommended_action": verdict.recommended_action,
        "triggered_rules": list(verdict.triggered_rules),
        "guardrails_hit": list(verdict.guardrails_hit),
        "report_path": report_path,
        "proposed_session_path": proposed_path,
        "ledger_entry_id": entry_id,
        "captured_at": snapshot.captured_at,
    }
