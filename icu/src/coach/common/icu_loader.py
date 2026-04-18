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

    ctl = summary.get("icu_ctl")
    atl = summary.get("icu_atl")
    tsb = (ctl - atl) if (ctl is not None and atl is not None) else None
    form = {
        "ctl": round(ctl, 1) if ctl is not None else None,
        "atl": round(atl, 1) if atl is not None else None,
        "tsb": round(tsb, 1) if tsb is not None else None,
    }

    description = summary.get("description") or ""
    if description:
        description = description[:500]

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
        "avg_hr": summary.get("average_heartrate"),
        "avg_cadence": summary.get("average_cadence"),
        "elevation_gain_m": summary.get("total_elevation_gain"),
        "decoupling_pct": summary.get("decoupling"),
        "avg_temperature_c": summary.get("average_temp"),
        "hr_drift_z2_bpm": None,  # not available in ICU; sub-analyzers tolerate None
        "planned_type": planned_type,
        "weight_kg": athlete_weight_kg,
        "form": form,
        "feel": summary.get("feel"),  # ICU RPE 1-5 (lower=better subjectively)
        "description": description,  # first 500 chars of user-written notes
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


def _classify_lap_type(
    zone: int | None,
    avg_power: int | float | None,
    duration_s: int,
    ftp: int,
) -> str:
    """Derive work/recovery/tempo/ride/warmup/cooldown from ICU zone + context.

    ICU labels every interval `type='WORK'` — useless for downstream filtering.
    We classify by power zone (1–7) the interval spent most time in:
      - zone 5+ → 'work'  (VO2max / anaerobic — the real hard intervals)
      - zone 4   → 'work' if >=120s, else 'surge'  (threshold efforts)
      - zone 3   → 'tempo'
      - zone 2   → 'z2'
      - zone 1   → 'recovery' if between other work intervals / short (<=600s),
                  else 'warmup_or_cooldown' for long (>600s) z1 blocks that
                  bookend the session
      - None/0   → fall back to FTP% threshold: >=90% → 'work', >=70% → 'tempo',
                  >=55% → 'z2', else 'recovery'
    """
    if zone is not None and zone >= 5:
        return "work"
    if zone == 4:
        return "work" if duration_s >= 120 else "surge"
    if zone == 3:
        return "tempo"
    if zone == 2:
        return "z2"
    if zone == 1:
        return "recovery" if duration_s <= 600 else "warmup_or_cooldown"
    # zone unknown — derive from FTP%
    if ftp and avg_power:
        pct = avg_power / ftp
        if pct >= 0.90:
            return "work"
        if pct >= 0.70:
            return "tempo"
        if pct >= 0.55:
            return "z2"
    return "recovery"


def _icu_type_to_internal(raw: str | None) -> str:
    """Legacy fallback when `zone` is missing. ICU's type field is normally
    useless ('WORK' for everything) so prefer _classify_lap_type."""
    if not raw:
        return "ride"
    u = str(raw).strip().upper()
    if u in ("INTERVAL", "EFFORT"):
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
    """Prefer structured icu_intervals; fall back to FIT laps.

    Output per lap includes coaching-relevant fields that let the LLM reason
    per-interval instead of guessing from aggregate session metrics:
      lap_index, type, label, zone, duration_s, avg_power, max_power,
      np_power, if, avg_hr, max_hr, avg_cadence, wbal_start_j, wbal_end_j,
      decoupling_pct, strain_score, joules_above_ftp.
    """
    out: list[dict] = []
    if icu_intervals:
        for idx, iv in enumerate(icu_intervals):
            duration = iv.get("moving_time") or iv.get("elapsed_time") or 0
            avg = iv.get("average_watts") or 0
            zone = iv.get("zone")
            lap_type = _classify_lap_type(zone, avg, duration, ftp)
            np_power = iv.get("weighted_average_watts")
            out.append(
                {
                    "lap_index": idx,  # 0-based internal index into icu_intervals
                    "lap_number": idx + 1,  # 1-based user-facing (matches ICU UI / 码表)
                    "type": lap_type,
                    "label": iv.get("label"),
                    "zone": zone,
                    "duration_s": duration,
                    "avg_power": avg,
                    "max_power": iv.get("max_watts"),
                    "np_power": np_power,
                    "if": round(avg / ftp, 3) if ftp and avg else None,
                    "avg_hr": iv.get("average_heartrate"),
                    "max_hr": iv.get("max_heartrate"),
                    "avg_cadence": iv.get("average_cadence"),
                    "wbal_start_j": iv.get("wbal_start"),
                    "wbal_end_j": iv.get("wbal_end"),
                    "decoupling_pct": iv.get("decoupling"),
                    "strain_score": iv.get("strain_score"),
                    "joules_above_ftp": iv.get("joules_above_ftp"),
                }
            )
        return out

    for idx, lap in enumerate(fit_laps or []):
        duration = lap.get("duration_sec") or 0
        avg = lap.get("avg_watts") or 0
        out.append(
            {
                "lap_index": idx,
                "lap_number": idx + 1,
                "type": _classify_lap_type(None, avg, duration, ftp),
                "label": None,
                "zone": None,
                "duration_s": duration,
                "avg_power": avg,
                "max_power": lap.get("max_watts"),
                "np_power": None,
                "if": round(avg / ftp, 3) if ftp and avg else None,
                "avg_hr": lap.get("avg_hr"),
                "max_hr": None,
                "avg_cadence": lap.get("avg_cadence"),
                "wbal_start_j": None,
                "wbal_end_j": None,
                "decoupling_pct": None,
                "strain_score": None,
                "joules_above_ftp": None,
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
