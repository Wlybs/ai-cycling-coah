from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal

from .types import KneeLoading, ResponseProfile, ResponseTypeStats

MIN_RECOVERY_HOURS = {
    "aerobic": 12,
    "tempo": 24,
    "threshold": 36,
    "vo2max": 48,
    "neuromuscular": 36,
    "race": 72,
}


def classify_tolerance(
    next_day_hrv_delta_pct: float,
    next_day_rhr_delta_bpm: float,
) -> Literal["low", "moderate", "high"]:
    if next_day_hrv_delta_pct <= -10 or next_day_rhr_delta_bpm >= 7:
        return "low"
    if next_day_hrv_delta_pct <= -5 or next_day_rhr_delta_bpm >= 3:
        return "moderate"
    return "high"


def _next_day(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (d + timedelta(days=1)).isoformat()


def build_profile(
    sessions: Iterable[dict],
    wellness_by_date: dict,
    window_days: int = 60,
) -> ResponseProfile:
    per_type: dict[str, list] = {}
    knee_minutes = 0
    knee_hr_drifts = []

    for s in sessions:
        per_type.setdefault(s["type"], []).append(s)
        knee_minutes += int(s.get("standing_climb_minutes") or 0)
        if "avg_hr_drift_bpm_standing" in s:
            knee_hr_drifts.append(float(s["avg_hr_drift_bpm_standing"]))

    types_out: dict[str, ResponseTypeStats] = {}
    for t, items in per_type.items():
        avg_tss = sum(i["tss"] for i in items) / len(items)
        hrv_deltas = []
        rhr_deltas = []
        adherences = []
        for i in items:
            w = wellness_by_date.get(_next_day(i["date"]))
            if w:
                hrv_deltas.append(w.get("hrv_delta_pct", 0))
                rhr_deltas.append(w.get("rhr_delta_bpm", 0))
            if i.get("planned_if"):
                adherences.append(1 if abs(i["if"] - i["planned_if"]) <= 0.05 else 0)

        hrv_avg = sum(hrv_deltas) / len(hrv_deltas) if hrv_deltas else 0.0
        rhr_avg = sum(rhr_deltas) / len(rhr_deltas) if rhr_deltas else 0.0
        tolerance = classify_tolerance(hrv_avg, rhr_avg)

        types_out[t] = ResponseTypeStats(
            sessions_n=len(items),
            avg_tss=int(round(avg_tss)),
            next_day_hrv_delta_pct=round(hrv_avg, 2),
            next_day_rhr_delta_bpm=round(rhr_avg, 2),
            avg_target_adherence=round(sum(adherences) / len(adherences), 2) if adherences else 0.0,
            tolerance_class=tolerance,
            recommended_min_interval_hours=MIN_RECOVERY_HOURS.get(t, 24),
        )

    avg_drift = sum(knee_hr_drifts) / len(knee_hr_drifts) if knee_hr_drifts else 0.0
    flag = None
    if knee_minutes > 120 or avg_drift > 8:
        flag = "caution"
    elif knee_minutes > 60 or avg_drift > 5:
        flag = "watch"

    return ResponseProfile(
        generated_at=datetime.now(timezone.utc).isoformat(),
        window_days=window_days,
        types=types_out,
        knee_loading=KneeLoading(
            standing_climb_minutes_90d=knee_minutes,
            avg_hr_drift_bpm_standing=round(avg_drift, 1),
            flag=flag,
        ),
    )
