"""Build a VerdictRequest payload from on-disk Phase 1/2/3 state.

Consumed by `scripts/prepare_verdict_request.py` and any caller that needs to
assemble the JSON for `scripts/run_consensus.py --verdict-request <path>`.

Pulls from:
  warehouse/2_Wellness/wellness_history.json    -> athlete_state + wellness_trend
  memory/plans/plan_<YYYYMMDD>.json (latest)    -> plan
  memory/periodization/phase_current.json       -> athlete_state.phase
  memory/periodization/periodization_current.json -> periodization_summary
  memory/physiology/{cp_w_current,durability,response_profile}.json -> physiology

Returns a dict that validates against
`src.coach.consensus.council_prompt.VerdictRequest`.
"""
from __future__ import annotations

import json
from datetime import date as DateT
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def _load_wellness_history(warehouse_dir: Path) -> list[dict]:
    path = warehouse_dir / "2_Wellness" / "wellness_history.json"
    if not path.exists():
        raise FileNotFoundError(f"wellness history not found: {path}")
    raw = _load_json(path)
    items = raw if isinstance(raw, list) else raw.get("wellness", [])
    # Sort ascending by id/date for stable ordering
    return sorted(items, key=lambda w: w.get("id") or w.get("date") or "")


def _load_latest_plan(memory_dir: Path) -> dict:
    plans_dir = memory_dir / "plans"
    if not plans_dir.exists():
        raise FileNotFoundError(f"plan directory missing: {plans_dir}")
    candidates = sorted(
        p for p in plans_dir.glob("plan_*.json")
        if not p.stem.endswith(".trace")
    )
    if not candidates:
        raise FileNotFoundError(f"no plan_*.json under {plans_dir}")
    return _load_json(candidates[-1])


def _load_phase(memory_dir: Path) -> str:
    path = memory_dir / "periodization" / "phase_current.json"
    if not path.exists():
        return "UNKNOWN"
    data = _load_json(path)
    phase = data.get("current_phase") or data.get("phase") or "UNKNOWN"
    return str(phase).upper()


def _load_periodization_summary(memory_dir: Path) -> dict:
    path = memory_dir / "periodization" / "periodization_current.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    summary = {
        "phase": str(data.get("current_phase", "UNKNOWN")).upper(),
        "weekly_tss_target": data.get("weekly_tss_target"),
        "weeks_to_race": data.get("weeks_to_race"),
        "focus_theme": data.get("focus_theme"),
    }
    return {k: v for k, v in summary.items() if v is not None}


def _load_physiology(memory_dir: Path) -> dict:
    phys_dir = memory_dir / "physiology"
    out: dict[str, Any] = {}
    cp_path = phys_dir / "cp_w_current.json"
    if cp_path.exists():
        cp = _load_json(cp_path)
        out["cp_w"] = cp.get("cp_watts")
        out["w_prime_j"] = cp.get("w_prime_joules")
    dur_path = phys_dir / "durability.json"
    if dur_path.exists():
        out["durability"] = _load_json(dur_path)
    rp_path = phys_dir / "response_profile.json"
    if rp_path.exists():
        out["response_profile"] = _load_json(rp_path)
    return out


def _compute_athlete_state(*, latest_wellness: dict, cp_w: dict | None,
                           phase: str, target_date: DateT) -> dict:
    ctl = latest_wellness.get("ctl") or 0.0
    atl = latest_wellness.get("atl") or 0.0
    tsb = latest_wellness.get("tsb")
    if tsb is None:
        tsb = ctl - atl
    w_prime = (cp_w or {}).get("w_prime_joules") or 0
    return {
        "ctl": float(ctl),
        "atl": float(atl),
        "tsb": float(tsb),
        "w_prime": int(w_prime),
        "phase": phase,
        "week_of_year": target_date.isocalendar().week,
    }


def build_verdict_request_payload(
    *, memory_dir: Path, warehouse_dir: Path, target_date: DateT,
    wellness_trend_days: int = 7,
) -> dict:
    """Assemble a VerdictRequest payload dict ready for run_consensus.py."""
    history = _load_wellness_history(warehouse_dir)
    if not history:
        raise FileNotFoundError(
            f"wellness history empty at {warehouse_dir}/2_Wellness/")
    latest = history[-1]

    plan = _load_latest_plan(memory_dir)
    phase = _load_phase(memory_dir)
    periodization_summary = _load_periodization_summary(memory_dir)
    physiology = _load_physiology(memory_dir)
    cp_w_raw = _load_json(memory_dir / "physiology" / "cp_w_current.json") \
        if (memory_dir / "physiology" / "cp_w_current.json").exists() else None
    athlete_state = _compute_athlete_state(
        latest_wellness=latest, cp_w=cp_w_raw,
        phase=phase, target_date=target_date,
    )

    trend = history[-wellness_trend_days:] if wellness_trend_days > 0 else []

    return {
        "plan": plan,
        "athlete_state": athlete_state,
        "physiology": physiology,
        "wellness_trend": trend,
        "periodization_summary": periodization_summary,
    }
