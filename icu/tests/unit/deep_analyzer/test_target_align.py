from src.coach.deep_analyzer.sub_analyzers.target_align import analyze, default_range


def test_default_range_vo2max():
    lo, hi = default_range("vo2max", cp=280)
    assert int(lo) == int(round(1.06 * 280))
    assert int(hi) == int(round(1.20 * 280))


def test_hit_when_time_in_zone_meets_threshold():
    activity = {
        "id": "iHit",
        "planned_type": "vo2max",
        "laps": [
            {"type": "work", "duration_s": 240, "avg_power": 320},
            {"type": "recovery", "duration_s": 120, "avg_power": 180},
            {"type": "work", "duration_s": 240, "avg_power": 320},
            {"type": "recovery", "duration_s": 120, "avg_power": 180},
            {"type": "work", "duration_s": 240, "avg_power": 320},
            {"type": "recovery", "duration_s": 120, "avg_power": 180},
            {"type": "work", "duration_s": 240, "avg_power": 320},
        ],
    }
    findings = analyze(activity, physiology={"cp_watts": 280})
    assert findings.verdict == "命中"


def test_miss_flags_coach_under_prescription_when_three_consecutive():
    activity = {
        "id": "iMiss",
        "planned_type": "vo2max",
        "laps": [{"type": "work", "duration_s": 300, "avg_power": 260}],
    }
    history = [{"type": "vo2max", "missed": True}, {"type": "vo2max", "missed": True}]
    findings = analyze(activity, physiology={"cp_watts": 280}, recent_misses=history)
    assert findings.metrics["under_prescription_flag"] is True
