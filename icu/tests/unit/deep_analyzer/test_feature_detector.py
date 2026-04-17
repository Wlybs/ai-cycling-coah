from src.coach.deep_analyzer.feature_detector import detect_features


def _activity(**overrides):
    base = {
        "id": "i1",
        "type": "Ride",
        "duration_s": 3600,
        "total_kj": 800,
        "elevation_gain_m": 150,
        "np_watts": 220,
        "max_hr": 170,
        "decoupling_pct": 4,
        "hr_drift_z2_bpm": 2,
        "avg_temperature_c": 22,
        "laps": [],
    }
    return {**base, **overrides}


def test_race_flag_by_type():
    f = detect_features(_activity(type="Race"), streams=None, physiology=None, athlete={"hr_max": 195})
    assert f.is_race is True


def test_race_flag_by_np_hr_combo_uses_cp():
    activity = _activity(np_watts=280, max_hr=190)
    physiology = {"cp_watts": 290}
    f = detect_features(activity, streams=None, physiology=physiology, athlete={"hr_max": 195})
    assert f.is_race is True


def test_intervals_detected_from_lap_if():
    activity = _activity(laps=[
        {"duration_s": 240, "if": 1.05},
        {"duration_s": 240, "if": 0.55},
        {"duration_s": 240, "if": 1.05},
    ])
    f = detect_features(activity, streams=None, physiology=None, athlete={"hr_max": 195})
    assert f.has_intervals is True


def test_heat_stress_requires_temp_present():
    f = detect_features(_activity(avg_temperature_c=None), streams=None, physiology=None, athlete={"hr_max": 195})
    assert f.heat_stress is False
    f2 = detect_features(_activity(avg_temperature_c=31), streams=None, physiology=None, athlete={"hr_max": 195})
    assert f2.heat_stress is True


def test_w_prime_depleted_reads_physiology():
    f = detect_features(_activity(), streams=None, physiology={"min_w_bal_pct": 10}, athlete={"hr_max": 195})
    assert f.w_prime_depleted is True
