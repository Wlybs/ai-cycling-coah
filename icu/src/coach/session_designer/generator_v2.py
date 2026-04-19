"""
Phase 2 File 10 (T45) — generate_plan_v2 facade.

Chains: periodization → design_week → save_weekly_plan/write_plan_trace → prose_render.
No LLM API call. Writes plan artifacts (JSON/MD/trace/prose) to disk.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date as DateT, datetime, timezone
from pathlib import Path
from typing import Optional

from src.coach.periodization import engine as periodization_engine
from src.coach.periodization.snapshot_io import load_periodization_snapshot
from src.coach.session_designer.assembler import design_week, write_plan_trace
from src.coach.session_designer.plan_writer import save_weekly_plan
from src.coach.session_designer.prose_io import render_prose_prompt


DEFAULT_FALLBACK_FTP = 280
PHYS_KEYS = ("cp_watts", "w_prime_joules", "durability_60s_pct", "knee_flag")


@dataclass
class GeneratePlanV2Result:
    """Result envelope for generate_plan_v2.

    Attributes:
        status: "ok" | "error"
        plan_json_path: Absolute path to plan_YYYYMMDD.json (or None on error)
        plan_md_path: Absolute path to plan_YYYYMMDD.md (or None on error)
        trace_path: Absolute path to plan_YYYYMMDD.trace.json (or None on error)
        prose_prompt_path: Absolute path to plan_YYYYMMDD.prose_prompt.md (or None on error)
        error: Error message (populated only if status == "error")
        violations: List of dicts (SafetyViolation.model_dump())
    """
    status: str
    plan_json_path: Optional[str] = None
    plan_md_path: Optional[str] = None
    trace_path: Optional[str] = None
    prose_prompt_path: Optional[str] = None
    error: Optional[str] = None
    violations: list = field(default_factory=list)


def _read_fallback_ftp(warehouse_dir: Path) -> int:
    """Read athlete FTP from warehouse profile, fallback to DEFAULT_FALLBACK_FTP.

    Args:
        warehouse_dir: Path to icu_data_warehouse root

    Returns:
        FTP (watts) from athlete.json, or DEFAULT_FALLBACK_FTP if not found
    """
    path = Path(warehouse_dir) / "1_Profile" / "athlete.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(data.get("ftp", DEFAULT_FALLBACK_FTP))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError, KeyError):
        return DEFAULT_FALLBACK_FTP


def _physiology_summary(memory_dir: Path) -> dict[str, object]:
    """Build physiology summary dict from coach_memory snapshots.

    Reads:
        - physiology/cp_w_current.json → cp_watts, w_prime_joules
        - physiology/durability.json → durability_60s_pct (decay_rate_pct_per_1000kj["60s"])
        - physiology/response_profile.json → knee_flag (knee_loading.flag)

    Missing or malformed files → None for that key.

    Args:
        memory_dir: Path to coach_memory root

    Returns:
        Dict with keys cp_watts, w_prime_joules, durability_60s_pct, knee_flag (all Optional).
    """
    result: dict[str, object] = {key: None for key in PHYS_KEYS}
    phys_dir = Path(memory_dir) / "physiology"

    # cp_w_current.json
    try:
        cp_w = json.loads((phys_dir / "cp_w_current.json").read_text(encoding="utf-8"))
        result["cp_watts"] = cp_w.get("cp_watts")
        result["w_prime_joules"] = cp_w.get("w_prime_joules")
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass

    # durability.json
    try:
        dur = json.loads((phys_dir / "durability.json").read_text(encoding="utf-8"))
        decay = dur.get("decay_rate_pct_per_1000kj", {})
        result["durability_60s_pct"] = decay.get("60s")
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass

    # response_profile.json
    try:
        resp = json.loads((phys_dir / "response_profile.json").read_text(encoding="utf-8"))
        knee = resp.get("knee_loading", {})
        result["knee_flag"] = knee.get("flag")
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass

    return result


def generate_plan_v2(
    week_start: DateT,
    week_end: DateT,
    warehouse_dir: Path,
    memory_dir: Path,
    reports_dir: Path,
    push_to_icu: bool = False,
) -> GeneratePlanV2Result:
    """Generate a complete weekly plan: periodization → design → save.

    Orchestrates the Phase 2 pipeline:
    1. Refresh periodization (phase detection → macro → meso → micro)
    2. Load resulting snapshot
    3. Design weekly plan from MicroCycle
    4. Write plan/trace/prose artifacts to disk
    5. Optionally push to ICU

    Args:
        week_start: Monday of the target week (date)
        week_end: Sunday of the target week (date)
        warehouse_dir: Path to icu_data_warehouse root
        memory_dir: Path to coach_memory root
        reports_dir: Output directory for plan artifacts
        push_to_icu: If True, call src.coach.plan_generator._push_to_icu(plan.model_dump())

    Returns:
        GeneratePlanV2Result with status, paths, and violations.
    """
    warehouse_dir = Path(warehouse_dir)
    memory_dir = Path(memory_dir)
    reports_dir = Path(reports_dir)

    # 1. Deterministic timestamp
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"

    # 2. Refresh periodization
    refresh = periodization_engine.refresh_periodization(
        warehouse_dir=warehouse_dir,
        memory_dir=memory_dir,
        reference_date=week_start,
        generated_at=now_iso,
    )

    # 3. Check refresh status
    if refresh.get("status") != "ok":
        return GeneratePlanV2Result(
            status="error",
            error=refresh.get("error") or "periodization failed",
        )

    # 4. Load snapshot
    snap = load_periodization_snapshot(Path(memory_dir) / "periodization")
    if snap is None:
        return GeneratePlanV2Result(
            status="error",
            error="periodization snapshot missing after refresh",
        )

    # 5. Read fallback FTP
    fallback_ftp = _read_fallback_ftp(warehouse_dir)

    # 6. Design week
    plan, sessions, violations = design_week(
        micro_cycle=snap.micro,
        memory_dir=memory_dir,
        fallback_ftp=fallback_ftp,
    )

    # 7. Build physiology summary
    physiology_summary = _physiology_summary(memory_dir)

    # 8. Render prose prompt
    prose_prompt_text = render_prose_prompt(
        plan=plan,
        phase_rationale=snap.micro.intent.rationale,
        phase_value=snap.current_phase.value,
        physiology_summary=physiology_summary,
        violations=[v.model_dump() for v in violations],
    )

    # 9. Create reports dir and save plan
    reports_dir.mkdir(parents=True, exist_ok=True)
    paths = save_weekly_plan(
        plan,
        reports_dir,
        prose_prompt=prose_prompt_text,
        trace=None,  # write_plan_trace handles trace separately
    )

    # 10. Write trace
    trace_path_str = write_plan_trace(
        reports_dir,
        week_start=week_start,
        sessions=sessions,
        violations=violations,
        generated_at=now_iso,
    )

    # 11. Push to ICU if requested
    if push_to_icu:
        # lazy import to avoid hard dep when push_to_icu=False
        from src.coach.plan_generator import _push_to_icu
        _push_to_icu(plan.model_dump())

    # 12. Build result
    return GeneratePlanV2Result(
        status="ok",
        plan_json_path=str(paths["json"]),
        plan_md_path=str(paths["md"]),
        trace_path=trace_path_str,
        prose_prompt_path=str(paths["prose_prompt"]),
        violations=[v.model_dump() for v in violations],
    )
