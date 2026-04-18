"""ICU warehouse adapter layer.

Phase 1 deep_analyzer + physiology code was written against a synthetic schema.
This module reshapes real Intervals.icu warehouse JSON into the internal shapes
Phase 1 consumers expect, so no sub_analyzer/feature_detector/composer has to
know about ICU's naming.

Real ICU warehouse layout under ``icu_data_warehouse/``:
  1_Profile/athlete_profile.json         -> dict with icu_ftp/icu_weight/weight
  3_PowerData/power_curves_*.json        -> {"list": [{..., "secs":[], "watts":[], "after_kj":0}, ...]}
  5_Activities_Detail/<date>_<id>.json   -> nested {summary, streams, laps, icu_intervals, ...}
                                            OR legacy flat {id, start_date_local, icu_pm_cp, ...}
  8_Events/events.json                   -> list of ICU calendar events
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator


# ---------------- summary ----------------


_TYPE_ALIASES = {
    "threshold": "sweet_spot",
    "sweetspot": "sweet_spot",
    "sweet_spot": "sweet_spot",
    "vo2": "vo2max",
    "vo2max": "vo2max",
    "race": "race",
    "endurance": "endurance",
    "recovery": "recovery",
    "ride": "ride",
}


def _normalize_activity_type(raw: str | None) -> str:
    if not raw:
        return "ride"
    key = str(raw).strip().lower().replace(" ", "_")
    return _TYPE_ALIASES.get(key, key or "ride")


def normalize_summary(
    summary: dict,
    *,
    athlete_ftp: int,
    athlete_weight_kg: float,
    events_by_date: dict | None = None,
) -> dict:
    """Map ICU summary keys -> Phase 1 internal keys. Never raises on missing fields."""
    start_local = summary.get("start_date_local") or ""
    date = start_local[:10] if start_local else ""

    icu_intensity = summary.get("icu_intensity")
    if_val = (icu_intensity / 100.0) if icu_intensity is not None else None

    icu_joules = summary.get("icu_joules")
    total_kj = int(icu_joules / 1000) if icu_joules is not None else None

    planned_type = None
    if events_by_date and date:
        planned_type = events_by_date.get(date)

    return {
        "id": summary.get("id"),
        "date": date,
        "type": _normalize_activity_type(summary.get("icu_intervals_type")),
        "duration_s": summary.get("moving_time"),
        "np_watts": summary.get("icu_weighted_avg_watts"),
        "tss": summary.get("icu_training_load"),
        "if": if_val,
        "total_kj": total_kj,
        "max_hr": summary.get("max_heartrate"),
        "elevation_gain_m": summary.get("total_elevation_gain"),
        "decoupling_pct": summary.get("decoupling"),
        "avg_temperature_c": summary.get("average_temp"),
        "hr_drift_z2_bpm": None,  # not available in ICU; sub-analyzers tolerate None
        "planned_type": planned_type,
        "weight_kg": athlete_weight_kg,
        "_raw": summary,
    }


# ---------------- streams ----------------


def _compute_gradient(
    altitude: list[float] | None,
    velocity_smooth: list[float] | None,
) -> list[float]:
    if not altitude:
        return []
    n = len(altitude)
    grad = [0.0] * n
    for i in range(1, n):
        da = (altitude[i] or 0) - (altitude[i - 1] or 0)
        # streams are 1 Hz; distance delta = velocity * 1s
        v = velocity_smooth[i] if velocity_smooth and i < len(velocity_smooth) else 0
        dd = max(float(v or 0), 1e-6)
        g = da / dd
        if abs(g) > 0.3:  # 30%+ is noise, not real
            g = 0.0
        grad[i] = g
    return grad


def normalize_streams(streams: dict) -> dict:
    """Return streams dict with Phase 1 keys: power, hr, gradient, cadence, altitude, time.

    Preserves w_bal and velocity_smooth for downstream use.
    """
    altitude = streams.get("altitude") or []
    velocity_smooth = streams.get("velocity_smooth") or []
    return {
        "power": streams.get("watts") or [],
        "hr": streams.get("heartrate") or [],
        "cadence": streams.get("cadence") or [],
        "altitude": altitude,
        "time": streams.get("time") or [],
        "gradient": _compute_gradient(altitude, velocity_smooth),
        "velocity_smooth": velocity_smooth,
        "w_bal": streams.get("w_bal") or [],
    }


# ---------------- laps ----------------


def _icu_type_to_internal(raw: str | None) -> str:
    if not raw:
        return "ride"
    u = str(raw).strip().upper()
    if u in ("WORK", "INTERVAL", "EFFORT"):
        return "work"
    if u in ("RECOVERY", "REST", "REST_INTERVAL"):
        return "recovery"
    return "ride"


def normalize_laps(
    icu_intervals: list,
    fit_laps: list,
    *,
    ftp: int,
) -> list[dict]:
    """Prefer structured icu_intervals; fall back to FIT laps."""
    out: list[dict] = []
    if icu_intervals:
        for idx, iv in enumerate(icu_intervals):
            duration = iv.get("moving_time") or iv.get("elapsed_time") or 0
            avg = iv.get("average_watts") or 0
            np_power = iv.get("weighted_average_watts")
            out.append(
                {
                    "lap_index": iv.get("number") if iv.get("number") is not None else idx,
                    "type": _icu_type_to_internal(iv.get("type")),
                    "duration_s": duration,
                    "avg_power": avg,
                    "np_power": np_power,
                    "if": (avg / ftp) if ftp and avg else None,
                }
            )
        return out

    for idx, lap in enumerate(fit_laps or []):
        duration = lap.get("duration_sec") or 0
        avg = lap.get("avg_watts") or 0
        out.append(
            {
                "lap_index": lap.get("lap_number") if lap.get("lap_number") is not None else idx,
                "type": "ride",  # FIT laps have no work/recovery distinction
                "duration_s": duration,
                "avg_power": avg,
                "np_power": None,
                "if": (avg / ftp) if ftp and avg else None,
            }
        )
    return out


# ---------------- events ----------------


def load_events_by_date(warehouse_dir: Path) -> dict[str, str]:
    """Read 8_Events/*.json; return {date_str -> planned_type_str}. Tolerant."""
    warehouse_dir = Path(warehouse_dir)
    events_dir = warehouse_dir / "8_Events"
    if not events_dir.exists():
        return {}
    out: dict[str, str] = {}
    for path in sorted(events_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        events: list
        if isinstance(doc, list):
            events = doc
        elif isinstance(doc, dict):
            events = doc.get("events") or [doc]
        else:
            continue
        for ev in events:
            if not isinstance(ev, dict):
                continue
            start = ev.get("start_date_local") or ev.get("date") or ""
            if not start:
                continue
            date = start[:10]
            label = (
                ev.get("sub_type")
                or ev.get("name")
                or ev.get("category")
                or ev.get("type")
            )
            if not label:
                continue
            planned = _normalize_activity_type(label)
            # Prefer first non-empty entry per date
            out.setdefault(date, planned)
    return out


# ---------------- athlete ----------------


def _load_athlete(warehouse_dir: Path) -> tuple[int, float]:
    """Return (ftp, weight_kg) with sensible fallbacks."""
    ftp = 288
    weight = 62.0
    path = warehouse_dir / "1_Profile" / "athlete_profile.json"
    if path.exists():
        try:
            prof = json.loads(path.read_text(encoding="utf-8"))
            ftp = int(prof.get("icu_ftp") or prof.get("ftp") or ftp)
            weight = float(prof.get("icu_weight") or prof.get("weight") or weight)
        except Exception:
            pass
    return ftp, weight


# ---------------- activity doc loader ----------------


def _is_nested(doc: dict) -> bool:
    return isinstance(doc, dict) and "summary" in doc and "streams" in doc


def _doc_activity_id(doc: dict) -> str | None:
    if _is_nested(doc):
        return doc.get("summary", {}).get("id")
    if isinstance(doc, dict):
        return doc.get("id")
    return None


def _iter_detail_files(warehouse_dir: Path) -> Iterator[Path]:
    detail_dir = warehouse_dir / "5_Activities_Detail"
    if not detail_dir.exists():
        return iter([])
    return iter(sorted(detail_dir.glob("*.json")))


def _build_activity_and_streams(
    doc: dict,
    *,
    ftp: int,
    weight: float,
    events_by_date: dict | None,
) -> tuple[dict | None, dict | None]:
    if not _is_nested(doc):
        # legacy flat: no streams/laps; pass a minimal normalized summary with streams=None
        summary = doc
        if not summary.get("id"):
            return None, None
        activity = normalize_summary(
            summary,
            athlete_ftp=ftp,
            athlete_weight_kg=weight,
            events_by_date=events_by_date,
        )
        activity["laps"] = []
        return activity, None

    summary = doc.get("summary") or {}
    streams_raw = doc.get("streams") or {}
    activity = normalize_summary(
        summary,
        athlete_ftp=ftp,
        athlete_weight_kg=weight,
        events_by_date=events_by_date,
    )
    activity["laps"] = normalize_laps(
        doc.get("icu_intervals") or [],
        doc.get("laps") or [],
        ftp=ftp,
    )
    streams = normalize_streams(streams_raw) if streams_raw else None
    return activity, streams


def load_activity_doc(
    warehouse_dir: Path,
    activity_id: str,
) -> tuple[dict, dict | None]:
    """Load one activity by id. Filename may include Chinese chars / _FULL suffix.

    Returns (activity_dict, streams_dict_or_None). Raises FileNotFoundError if not found.
    Streams is None for legacy flat files.
    """
    warehouse_dir = Path(warehouse_dir)
    ftp, weight = _load_athlete(warehouse_dir)
    events_by_date = load_events_by_date(warehouse_dir)

    for path in _iter_detail_files(warehouse_dir):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if _doc_activity_id(doc) == activity_id:
            activity, streams = _build_activity_and_streams(
                doc, ftp=ftp, weight=weight, events_by_date=events_by_date
            )
            if activity is None:
                break
            return activity, streams

    raise FileNotFoundError(
        f"No activity file found in {warehouse_dir / '5_Activities_Detail'} matching id={activity_id!r}"
    )


def iter_activity_docs(
    warehouse_dir: Path,
) -> Iterable[tuple[dict, dict | None]]:
    """Yield (activity, streams) for every nested detail file.

    Legacy flat files are skipped (no streams/laps). Caller gets only usable docs.
    """
    warehouse_dir = Path(warehouse_dir)
    ftp, weight = _load_athlete(warehouse_dir)
    events_by_date = load_events_by_date(warehouse_dir)

    for path in _iter_detail_files(warehouse_dir):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not _is_nested(doc):
            continue
        activity, streams = _build_activity_and_streams(
            doc, ftp=ftp, weight=weight, events_by_date=events_by_date
        )
        if activity is None:
            continue
        yield activity, streams
