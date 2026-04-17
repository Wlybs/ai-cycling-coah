from typing import Optional

from .types import Features

_CLIMBING_RUN_SAMPLES = 180  # 3 min at 1 Hz stream resolution


def detect_features(
    activity: dict,
    streams: Optional[dict],
    physiology: Optional[dict],
    athlete: dict,
) -> Features:
    hr_max = int(athlete.get("hr_max") or 0) or None
    cp = None
    if physiology:
        cp = physiology.get("cp_watts")

    is_race = (activity.get("type", "").lower() == "race")
    if not is_race and cp and hr_max:
        np = activity.get("np_watts") or 0
        mhr = activity.get("max_hr") or 0
        if np > 0.95 * cp and mhr > 0.95 * hr_max:
            is_race = True

    laps = activity.get("laps") or []
    has_intervals = any(
        (lap.get("if") or 0) > 0.85 and 30 <= (lap.get("duration_s") or 0) <= 600
        for lap in laps
    )

    elev = activity.get("elevation_gain_m") or 0
    has_climbing = elev > 300
    if streams and "gradient" in streams:
        grades = streams["gradient"]
        run = 0
        for g in grades:
            if g is not None and g > 5:
                run += 1
                if run > _CLIMBING_RUN_SAMPLES:
                    has_climbing = True
                    break
            else:
                run = 0

    duration_s = int(activity.get("duration_s") or 0)
    is_endurance_long = duration_s > 7200

    if_val = max((l.get("if") or 0) for l in laps) if laps else (activity.get("if") or 0)
    decoupling = activity.get("decoupling_pct")
    hr_drift_z2 = activity.get("hr_drift_z2_bpm") or 0
    has_anomaly = (
        if_val > 0.90
        or (decoupling is not None and decoupling > 8)
        or hr_drift_z2 > 10
    )

    target_type = activity.get("planned_type") or None
    if not target_type and activity.get("type"):
        t = activity["type"].lower()
        if t in ("vo2max", "threshold", "tempo", "aerobic", "neuromuscular", "race"):
            target_type = t

    w_prime_depleted = bool(physiology and (physiology.get("min_w_bal_pct") or 100) < 20)

    temp = activity.get("avg_temperature_c")
    heat_stress = temp is not None and temp > 28

    return Features(
        has_intervals=has_intervals,
        is_race=is_race,
        has_climbing=has_climbing,
        is_endurance_long=is_endurance_long,
        has_anomaly=has_anomaly,
        target_type_claimed=target_type,
        w_prime_depleted=w_prime_depleted,
        heat_stress=bool(heat_stress),
        duration_seconds=duration_s,
        total_kj=int(activity.get("total_kj") or 0),
    )
