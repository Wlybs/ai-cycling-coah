from src.coach.deep_analyzer.sub_analyzers.climbing import analyze


def test_segments_climb_and_computes_wkg():
    streams = {
        "power": [320] * 600,
        "gradient": [6] * 600,
        "cadence": [82] * 600,
        "hr": [165] * 600,
        "altitude": list(range(0, 600)),
    }
    activity = {"id": "iClimb", "weight_kg": 62}
    findings = analyze(activity, streams=streams, physiology={"cp_watts": 280})
    c = findings.metrics["climbs"][0]
    assert abs(c["avg_power_w"] - 320) <= 2
    assert 5.1 <= c["avg_wkg"] <= 5.3
    assert c["vam_mh"] > 0


def test_standing_inference_low_cadence_high_power():
    streams = {
        "power": [340] * 600,
        "gradient": [7] * 600,
        "cadence": [65] * 600,
        "hr": [170] * 600,
        "altitude": list(range(0, 1200, 2)),
    }
    activity = {"id": "iStand", "weight_kg": 62}
    findings = analyze(activity, streams=streams, physiology={"cp_watts": 280})
    assert findings.metrics["standing_minutes"] >= 8
