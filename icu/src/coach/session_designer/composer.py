"""把 WorkoutTemplate + 生理数据变成一个 DesignedSession。"""
from __future__ import annotations

import math
from datetime import date as DateT
from typing import Any, Optional

from ..periodization.types import SessionType
from .types import (
    DesignedSession, SessionIntent, SessionStructure, WorkoutStep,
)
from .workout_library import (
    WorkoutTemplate, WorkoutTemplateStep, get_template,
)

TSS_STEP_COEF = 100.0


def _mid(low: Optional[float], high: Optional[float]) -> Optional[float]:
    """Compute midpoint of two optional floats."""
    if low is None or high is None:
        return None
    return (low + high) / 2.0


def _step_watts(
    step: WorkoutTemplateStep, cp: int
) -> tuple[Optional[int], Optional[int]]:
    """Convert pct_of_cp to absolute watts."""
    if step.pct_of_cp_low is None or step.pct_of_cp_high is None:
        return (None, None)
    return (int(round(step.pct_of_cp_low * cp)),
            int(round(step.pct_of_cp_high * cp)))


def _step_tss(step: WorkoutTemplateStep) -> float:
    """Estimate TSS for a single step: (duration_s / 3600) * IF^2 * 100."""
    mid = _mid(step.pct_of_cp_low, step.pct_of_cp_high)
    if mid is None:
        return 0.0
    return (step.duration_s / 3600.0) * (mid ** 2) * TSS_STEP_COEF


def _convert_step(tpl_step: WorkoutTemplateStep, cp: int) -> WorkoutStep:
    """Convert a template step to a designed step with absolute watts."""
    low, high = _step_watts(tpl_step, cp)
    return WorkoutStep(
        label=tpl_step.label,
        duration_s=tpl_step.duration_s,
        target_w_low=low, target_w_high=high,
        zone=tpl_step.zone,
    )


def _scale_long_ride_to_tss(
    template: WorkoutTemplate, cp: int, target_tss: int
) -> tuple[list[WorkoutStep], float]:
    """
    Scale endurance template main section to hit target TSS.
    Returns (scaled_steps, stretch_factor).
    """
    converted = [_convert_step(s, cp) for s in template.steps]
    main_indices = [i for i, s in enumerate(template.steps)
                    if s.label not in ("WU", "CD")
                    and s.pct_of_cp_low is not None
                    and s.pct_of_cp_low < 0.80]
    if not main_indices:
        return converted, 1.0

    estimated = sum(_step_tss(template.steps[i]) for i in range(len(template.steps)))
    main_tss = sum(_step_tss(template.steps[i]) for i in main_indices)
    if main_tss <= 0 or estimated <= 0:
        return converted, 1.0

    needed = target_tss - (estimated - main_tss)
    non_main_s = sum(
        template.steps[i].duration_s
        for i in range(len(template.steps))
        if i not in main_indices
    )
    if needed <= 0:
        stretch = template.total_duration_s_range[0] / sum(
            s.duration_s for s in template.steps)
    else:
        main_seconds = sum(template.steps[i].duration_s for i in main_indices)
        main_tss_per_s = main_tss / main_seconds
        new_main_seconds = max(600, needed / main_tss_per_s)
        stretch = new_main_seconds / main_seconds
        total_s = stretch * main_seconds + non_main_s
        lo, hi = template.total_duration_s_range
        if total_s > hi:
            stretch = (hi - non_main_s) / main_seconds
        elif total_s < lo:
            stretch = (lo - non_main_s) / main_seconds

    for i in main_indices:
        orig = converted[i]
        converted[i] = WorkoutStep(
            label=orig.label,
            duration_s=int(round(template.steps[i].duration_s * stretch)),
            target_w_low=orig.target_w_low,
            target_w_high=orig.target_w_high,
            zone=orig.zone,
        )
    return converted, stretch


def _power_range_summary(steps: list[WorkoutStep]) -> Optional[str]:
    """Extract min-max watts from main (non-WU/CD) steps."""
    main = [s for s in steps if s.label not in ("WU", "CD", "rest")
            and s.target_w_low is not None and s.target_w_high is not None]
    if not main:
        return None
    lo = min(s.target_w_low for s in main)
    hi = max(s.target_w_high for s in main)
    return f"{lo}-{hi}W"


def _build_description(
    template: WorkoutTemplate, steps: list[WorkoutStep]
) -> str:
    """Build one-line description: WU; main; CD with watts."""
    parts: list[str] = []
    for s in steps:
        minutes = max(1, round(s.duration_s / 60))
        if s.target_w_low is not None and s.target_w_high is not None:
            parts.append(f"{s.label} {minutes}min @ {s.target_w_low}-{s.target_w_high}W")
        else:
            parts.append(f"{s.label} {minutes}min")
    return "; ".join(parts)


def _session_display_name(template: WorkoutTemplate, cp: int) -> str:
    """Generate user-facing session name with power range."""
    mapping = {
        "vo2max_short_5x4": f"VO2max 5×4' @ {int(cp*1.10)}-{int(cp*1.15)}W",
        "vo2max_short_6x3": f"VO2max 6×3' @ {int(cp*1.15)}-{int(cp*1.20)}W",
        "threshold_2x20": f"Threshold 2×20' @ {int(cp*0.97)}-{int(cp*1.02)}W",
        "sweet_spot_3x15": f"Sweet-spot 3×15' @ {int(cp*0.88)}-{int(cp*0.93)}W",
        "tempo_continuous_60": f"Tempo 60' @ {int(cp*0.80)}-{int(cp*0.85)}W",
        "endurance_long_z2": "Long Z2 endurance",
        "endurance_long_with_tempo": "Long endurance + tempo",
        "recovery_spin": "Recovery spin",
        "openers_short": "Openers 4×30''",
        "race_sim_course": "Race simulation",
        "rest_day": "Rest",
    }
    return mapping.get(template.name, template.name)


def compose_session(
    intent: SessionIntent,
    date: DateT,
    template_name: str,
    physiology: dict[str, Any],
    durability: dict[str, Any],
    response_profile: dict[str, Any],
) -> DesignedSession:
    """
    Convert WorkoutTemplate + SessionIntent + physiology into DesignedSession.

    Algorithm:
    1. Resolve target watts: pct_of_cp * cp_watts
    2. Duration scaling: for endurance_* templates, stretch main section to hit target_tss
    3. TSS estimation: sum of (duration_s / 3600) * IF^2 * 100 across steps
    4. Power range: min-max from main steps
    5. Description: skeleton with watts
    6. Trace: {template_name, cp, w_prime, tss_est, tss_target, duration_stretch, durability}
    """
    template = get_template(template_name)
    cp = int(physiology.get("cp_watts") or physiology.get("athlete_ftp_set") or 280)
    w_prime = int(physiology.get("w_prime_joules") or 20000)

    stretch = 1.0
    if template.name.startswith("endurance_long") and intent.target_tss > 0:
        steps, stretch = _scale_long_ride_to_tss(template, cp, intent.target_tss)
    else:
        steps = [_convert_step(s, cp) for s in template.steps]

    structure = SessionStructure(steps=steps)
    total_min = max(0, int(math.ceil(structure.total_duration_s / 60)))

    tss_est = 0.0
    for s in steps:
        mid = _mid(
            (s.target_w_low / cp) if s.target_w_low is not None else None,
            (s.target_w_high / cp) if s.target_w_high is not None else None,
        )
        if mid is None:
            continue
        tss_est += (s.duration_s / 3600.0) * (mid ** 2) * TSS_STEP_COEF

    final_tss = intent.target_tss
    if template.name.startswith("endurance_long"):
        final_tss = intent.target_tss
    else:
        diff_pct = abs(tss_est - intent.target_tss) / max(intent.target_tss, 1)
        final_tss = intent.target_tss if diff_pct <= 0.15 else int(round(tss_est))

    # Case-insensitive lookup: response_profile["types"] keys may be lowercase
    # (from physiology.response_profile) but SessionType.value is Title Case.
    type_key = template.session_type.value
    types_dict = response_profile.get("types") or {}
    tolerance_entry: dict = {}
    for k, v in types_dict.items():
        if isinstance(k, str) and k.lower() == type_key.lower():
            tolerance_entry = v or {}
            break

    trace = {
        "template_name": template.name,
        "cp_watts": cp,
        "w_prime_joules": w_prime,
        "tss_estimated": round(tss_est, 1),
        "tss_target": intent.target_tss,
        "duration_stretched_pct": round((stretch - 1.0) * 100, 1),
        "durability_applied": bool(durability.get("decay_rate_pct_per_1000kj")),  # T42 will consume decay rate; today this is a presence flag only
        "tolerance_class": tolerance_entry.get("tolerance_class"),
    }

    return DesignedSession(
        day_of_week=intent.day_of_week,
        date=date.isoformat(),
        session_type=template.session_type,
        name=_session_display_name(template, cp),
        description=_build_description(template, steps),
        duration_min=total_min,
        target_tss=max(0, min(400, int(final_tss))),
        structure=structure,
        power_range_w=_power_range_summary(steps),
        trace=trace,
    )
