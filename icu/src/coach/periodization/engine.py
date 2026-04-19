"""Periodization engine facade — orchestrates phase detection, macro/meso/micro planning.

Responsibilities:
1. Load wellness history, athlete profile, race calendar, stimulus data
2. Analyze CTL slope and detect current phase
3. Plan macro periodization and select meso pattern
4. Build meso block and micro cycle
5. Emit PeriodizationSnapshot and structured logs
"""
from __future__ import annotations

import json
import statistics
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from ..common.logging import get_logger
from .ctl_slope import analyze_ctl_slope
from .intent_library import build_intent_for_phase
from .macro_planner import plan_macro
from .meso_builder import build_meso_block, select_meso_pattern
from .micro_cycle import build_micro_cycle
from .phase_detector import detect_phase
from .race_calendar import load_race_calendar, next_race_after
from .snapshot_io import write_periodization_snapshot
from .types import (
    MacroWindow, NextRace, Phase, PeriodizationSnapshot,
)

LOG = get_logger("periodization_engine")


def _load_wellness(warehouse_dir: Path) -> list[dict]:
    """Load wellness history from warehouse, return empty list on error."""
    path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _load_athlete(warehouse_dir: Path) -> dict:
    """Load athlete profile from warehouse, return empty dict on error.

    Note: athlete dict is currently unused by engine helpers; reserved for
    future knee-safety knob / response profile integration.
    """
    path = warehouse_dir / "1_Profile" / "athlete.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_stimulus_median(memory_dir: Path) -> Optional[float]:
    """Median stimulus_score from coach_memory/deep_analysis/*.trace.json.

    Walks recent .trace.json files in descending mtime order, collects stimulus_score
    values from the 5 most recent files, returns their median. Falls back to
    summary_latest.json if no .trace files have stimulus_score. Returns None if nothing found.
    """
    deep_dir = memory_dir / "deep_analysis"
    if not deep_dir.exists():
        return None

    scores: list[float] = []
    # Sort by mtime descending, take up to 5 most recent
    trace_files = sorted(
        deep_dir.glob("*.trace.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:5]

    for trace_path in trace_files:
        try:
            doc = json.loads(trace_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        stimulus = doc.get("stimulus_score")
        if isinstance(stimulus, (int, float)):
            scores.append(float(stimulus))

    if scores:
        return statistics.median(scores)

    # Fallback: summary_latest.json
    summary_path = deep_dir / "summary_latest.json"
    if summary_path.exists():
        try:
            doc = json.loads(summary_path.read_text(encoding="utf-8"))
            stimulus = doc.get("stimulus_score")
            if isinstance(stimulus, (int, float)):
                return float(stimulus)
        except (json.JSONDecodeError, OSError):
            pass

    return None


def _load_knee_flag(memory_dir: Path) -> Optional[str]:
    """Load knee-loading safety flag from physiology/response_profile.json.

    Returns the 'flag' value from doc['knee_loading'] if present, else None.
    """
    path = memory_dir / "physiology" / "response_profile.json"
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        knee_loading = doc.get("knee_loading") or {}
        return knee_loading.get("flag")
    except (json.JSONDecodeError, OSError):
        return None


def _locate_window(windows: list[MacroWindow], ref: date) -> MacroWindow:
    """Find the MacroWindow containing ref, fallback to nearest by date."""
    if not windows:
        raise ValueError("_locate_window: windows list is empty")
    for w in windows:
        if w.start_date <= ref <= w.end_date:
            return w
    # Fallback: closest by absolute days distance
    return min(windows, key=lambda w: abs((w.start_date - ref).days))


def _monday_of(d: date) -> date:
    """Return the Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def refresh_periodization(
    warehouse_dir: Path,
    memory_dir: Path,
    reference_date: date,
    generated_at: str,
) -> dict:
    """Orchestrate full periodization refresh: phase detection → macro → meso → micro.

    Args:
        warehouse_dir: Path to icu_data_warehouse root (contains 2_Wellness, 8_Events, 1_Profile)
        memory_dir: Path to coach_memory root (contains deep_analysis, physiology, etc.)
        reference_date: Date to plan around (typically "today")
        generated_at: ISO8601 timestamp of generation

    Returns:
        On success: {"status": "ok", "phase": str, "reasons": list[str], "snapshot_path": str|Path}
        On error: {"status": "error", "error": str}
    """
    t0 = time.monotonic()
    warehouse_dir = Path(warehouse_dir)
    memory_dir = Path(memory_dir)

    try:
        # Load raw data
        wellness = _load_wellness(warehouse_dir)
        _athlete = _load_athlete(warehouse_dir)  # Unused now, reserved for future

        # Extract baseline CTL from latest wellness entry
        baseline_ctl = 90.0
        if wellness:
            ctl_entries = [w for w in wellness if w.get("ctl") is not None]
            if ctl_entries:
                baseline_ctl = float(ctl_entries[-1]["ctl"])

        # Analyze CTL slope
        slope = analyze_ctl_slope(
            wellness, reference_date=reference_date, window_days=28)

        # Load races and find next race after reference_date
        races = load_race_calendar(warehouse_dir, memory_dir)
        nxt = next_race_after(races, reference_date)

        # Compute 90-day CTL peak (used for phase detection fallback)
        ctl_90d_peak = 0.0
        for w in wellness:
            try:
                entry_date = date.fromisoformat(str(w.get("id", ""))[:10])
            except (ValueError, TypeError):
                continue
            if (reference_date - entry_date).days <= 90 and w.get("ctl") is not None:
                ctl_90d_peak = max(ctl_90d_peak, float(w["ctl"]))

        # Load recent stimulus median
        stimulus_median = _load_stimulus_median(memory_dir)

        # Detect phase
        phase, reasons = detect_phase(
            reference_date=reference_date,
            ctl_slope=slope,
            races=races,
            ctl_90d_peak=ctl_90d_peak or baseline_ctl,
            recent_stimulus_median=stimulus_median,
        )

        # Plan macro periodization
        macro = plan_macro(
            reference_date=reference_date,
            baseline_ctl=baseline_ctl,
            races=races,
            generated_at=generated_at,
        )

        # Locate current macro window
        window = _locate_window(macro.windows, reference_date)

        # Select meso pattern and build meso block
        knee = _load_knee_flag(memory_dir)
        pattern = select_meso_pattern(
            phase=window.phase,
            knee_flag=knee,
            recent_atl_delta=0.0,
            response_high_responder=False,
        )
        meso = build_meso_block(
            reference_date=reference_date,
            macro=window,
            pattern=pattern,
        )

        # Build phase intent and micro cycle
        intent = build_intent_for_phase(window.phase, baseline_ctl)
        week_monday = _monday_of(reference_date)
        week_idx = max(0, (week_monday - meso.block_start).days // 7)
        micro = build_micro_cycle(
            week_start=week_monday,
            meso=meso,
            intent=intent,
            week_idx=week_idx,
        )

        # Assemble next_race snapshot (NextRace has no days_out field)
        next_race = None
        if nxt is not None:
            next_race = NextRace(
                name=nxt.name,
                race_date=nxt.race_date,
                priority=nxt.priority,
                course_hint=nxt.course_hint,
            )

        # Assemble and write snapshot
        snap = PeriodizationSnapshot(
            generated_at=generated_at,
            current_phase=phase,
            macro=macro,
            meso=meso,
            micro=micro,
            next_race=next_race,
        )
        snapshot_path = write_periodization_snapshot(
            memory_dir / "periodization", snap)

        # Log success
        LOG.event(
            action="refresh_periodization",
            duration_ms=int((time.monotonic() - t0) * 1000),
            status="ok",
            phase=phase.value,
            reasons_count=len(reasons),
            snapshot_path=str(snapshot_path),
        )

        return {
            "status": "ok",
            "phase": phase.value,
            "reasons": reasons,
            "snapshot_path": snapshot_path,
        }

    except Exception as e:
        # Log error with duration
        error_msg = f"{type(e).__name__}: {e}"
        LOG.event(
            action="refresh_periodization",
            duration_ms=int((time.monotonic() - t0) * 1000),
            status="error",
            error=error_msg,
            error_type=type(e).__name__,
        )
        return {"status": "error", "error": error_msg}
