from src.coach.physiology.response_profile import build_profile, classify_tolerance


def test_classify_tolerance_rules():
    # Tiny HRV dip + tiny RHR bump → high
    assert classify_tolerance(next_day_hrv_delta_pct=-2.0, next_day_rhr_delta_bpm=1.0) == "high"
    # Moderate HRV hit → moderate
    assert classify_tolerance(next_day_hrv_delta_pct=-7.0, next_day_rhr_delta_bpm=4.0) == "moderate"
    # Big HRV drop → low
    assert classify_tolerance(next_day_hrv_delta_pct=-15.0, next_day_rhr_delta_bpm=8.0) == "low"


def test_build_profile_assigns_tolerance_and_knee_flag():
    sessions = [
        {"type": "vo2max", "date": "2026-04-10", "tss": 85, "if": 0.92, "planned_if": 0.95, "standing_climb_minutes": 6, "avg_hr_drift_bpm_standing": 4.0},
        {"type": "vo2max", "date": "2026-04-14", "tss": 90, "if": 0.93, "planned_if": 0.95, "standing_climb_minutes": 5, "avg_hr_drift_bpm_standing": 5.0},
    ]
    wellness = {
        "2026-04-11": {"hrv_delta_pct": -4, "rhr_delta_bpm": 2},
        "2026-04-15": {"hrv_delta_pct": -5, "rhr_delta_bpm": 3},
    }
    profile = build_profile(sessions=sessions, wellness_by_date=wellness, window_days=60)
    assert "vo2max" in profile.types
    assert profile.types["vo2max"].sessions_n == 2
    assert profile.types["vo2max"].tolerance_class in ("moderate", "high")
    assert profile.knee_loading.standing_climb_minutes_90d == 11
