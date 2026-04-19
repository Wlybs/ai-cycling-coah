"""MicroCycle → WeeklyPlan。"""
from __future__ import annotations

import json
from datetime import date as DateT, timedelta
from pathlib import Path
from typing import Any, Optional

from ..periodization.types import (
    DayIntent, IntensityTier, MicroCycle, SessionType,
)
from .composer import compose_session
from .intent_translator import translate_intent
from .safety_guards import SafetyViolation, check_weekly_plan
from .types import (
    DayPlanV2, DesignedSession, SessionIntent, WeeklyPlan,
)

DOW_DATES = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
             "Fri": 4, "Sat": 5, "Sun": 6}
DEFAULT_W_PRIME = 20000    # Joules — used only when cp_w_current.json missing/incomplete
MIN_CP = 100               # Watts — sanity floor for fallback_ftp


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_physiology(
    memory_dir: Path, fallback_ftp: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    phys_dir = memory_dir / "physiology"
    cp_w = _load_json(phys_dir / "cp_w_current.json")
    if not cp_w:
        cp_w = {"cp_watts": max(fallback_ftp, MIN_CP),
                "w_prime_joules": DEFAULT_W_PRIME,
                "fit_r_squared": None,
                "athlete_ftp_set": fallback_ftp}
    dur = _load_json(phys_dir / "durability.json") or {}
    resp = _load_json(phys_dir / "response_profile.json") or {}
    return cp_w, dur, resp


def _tolerance_classes(resp: dict[str, Any]) -> dict[str, str]:
    types = (resp or {}).get("types") or {}
    out: dict[str, str] = {}
    for k, v in types.items():
        tc = (v or {}).get("tolerance_class")
        if tc is not None:
            out[k] = tc
    return out


def _session_to_dayplan(s: DesignedSession) -> DayPlanV2:
    icu_type = "Rest" if s.session_type is SessionType.REST else "Ride"
    return DayPlanV2(
        date=s.date,
        day_of_week=s.day_of_week,
        training_type=s.session_type.value,
        icu_type=icu_type,
        name=s.name,
        description=s.description,
        duration_min=s.duration_min,
        target_tss=s.target_tss,
        power_range_w=s.power_range_w,
        hr_range_bpm=s.hr_range_bpm,
    )


def _revise_for_violations(
    days_intents: list[dict[str, Any]], violations: list[SafetyViolation]
) -> list[dict[str, Any]]:
    """基于 violations 做一次保守修订。规则同 safety_guards 的 suggested_action。"""
    out = [dict(d) for d in days_intents]
    for v in violations:
        if v.rule == "hard_back_to_back" and v.day_index is not None:
            out[v.day_index]["tier"] = "MEDIUM"
            out[v.day_index]["session_hint"] = "sweet-spot 3x12'"
        elif v.rule == "knee_back_to_back_stand" and v.day_index is not None:
            out[v.day_index]["tier"] = "EASY"
            out[v.day_index]["session_hint"] = "recovery spin"
        elif v.rule == "w_prime_weekly_overdraw":
            hard_indices = [i for i, d in enumerate(out)
                            if str(d.get("tier", "")).upper() == "HARD"]
            for idx in hard_indices[3:]:
                out[idx]["tier"] = "MEDIUM"
                out[idx]["session_hint"] = "sweet-spot 3x12'"
        elif v.rule == "tss_budget_overflow":
            for i in range(len(out) - 1, -1, -1):
                if out[i].get("tier") == "EASY" and out[i].get("target_tss", 0) > 0:
                    out[i]["target_tss"] = max(
                        0, int(out[i]["target_tss"] * 0.7))
                    break
        elif v.rule == "missing_rest_day":
            out[4]["tier"] = "REST"
            out[4]["session_hint"] = "rest"
            out[4]["target_tss"] = 0
    return out


def design_week(
    micro_cycle: MicroCycle,
    memory_dir: Path,
    fallback_ftp: int = 280,
) -> tuple[WeeklyPlan, list[DesignedSession], list[SafetyViolation]]:
    """Design a weekly plan from a MicroCycle with safety-check and auto-revision.

    Args:
        micro_cycle: The week's 7-day intent sequence.
        memory_dir: Path to coach_memory directory (contains physiology/ JSONs).
        fallback_ftp: Default CP (watts) if cp_w_current.json missing.

    Returns:
        (WeeklyPlan, list[DesignedSession], remaining_violations)
    """
    memory_dir = Path(memory_dir)
    phys, dur, resp = _load_physiology(memory_dir, fallback_ftp)
    tol = _tolerance_classes(resp)

    # 1) intent dict list for safety + revision
    day_dicts: list[dict[str, Any]] = []
    for di in micro_cycle.days:
        day_dicts.append({
            "day_of_week": di.day_of_week,
            "tier": di.tier.value,
            "target_tss": di.target_tss,
            "session_hint": di.session_hint,
        })

    # 2) first safety check → revise once
    w_prime = int(phys.get("w_prime_joules") or DEFAULT_W_PRIME)
    first_violations = check_weekly_plan(
        day_dicts, weekly_tss_target=micro_cycle.weekly_tss_target,
        response_profile=resp, durability=dur, w_prime_joules=w_prime,
    )
    revised = _revise_for_violations(day_dicts, first_violations)

    # 3) re-check → remaining
    remaining = check_weekly_plan(
        revised, weekly_tss_target=micro_cycle.weekly_tss_target,
        response_profile=resp, durability=dur, w_prime_joules=w_prime,
    )

    # 4) compose sessions
    sessions: list[DesignedSession] = []
    for day in revised:
        tier = IntensityTier(day["tier"])
        intent = SessionIntent(
            day_of_week=day["day_of_week"], tier=tier,
            target_tss=int(day["target_tss"]),
            session_hint=day["session_hint"],
        )
        template_name = translate_intent(
            tier=tier, hint=day["session_hint"],
            tolerance_classes=tol,
        )
        day_date = micro_cycle.week_start + timedelta(
            days=DOW_DATES[day["day_of_week"]])
        session = compose_session(
            intent=intent, date=day_date,
            template_name=template_name,
            physiology=phys, durability=dur,
            response_profile=resp,
        )
        sessions.append(session)

    # 5) WeeklyPlan
    plan = WeeklyPlan(
        week_start=micro_cycle.week_start.isoformat(),
        week_end=micro_cycle.week_end.isoformat(),
        focus_theme=(f"{micro_cycle.phase.value} week — "
                     f"primary: {micro_cycle.intent.primary_adaptation}"),
        weekly_tss_target=micro_cycle.weekly_tss_target,
        coaching_summary="",
        days=[_session_to_dayplan(s) for s in sessions],
    )

    return plan, sessions, remaining
