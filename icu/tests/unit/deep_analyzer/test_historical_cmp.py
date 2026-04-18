from src.coach.deep_analyzer.sub_analyzers.historical_cmp import analyze


def test_progression_detected():
    current = {"id": "iNow", "type": "vo2max", "duration_s": 3600, "np_watts": 290, "decoupling_pct": 3}
    history = [
        {"id": "i1", "type": "vo2max", "duration_s": 3400, "np_watts": 275, "decoupling_pct": 5},
        {"id": "i2", "type": "vo2max", "duration_s": 3500, "np_watts": 272, "decoupling_pct": 5},
        {"id": "i3", "type": "vo2max", "duration_s": 3800, "np_watts": 270, "decoupling_pct": 6},
    ]
    findings = analyze(current, history=history)
    assert findings.verdict in ("进步", "持平")


def test_regression_detected():
    current = {"id": "iNow", "type": "vo2max", "duration_s": 3600, "np_watts": 250, "decoupling_pct": 9}
    history = [
        {"id": "i1", "type": "vo2max", "duration_s": 3600, "np_watts": 290, "decoupling_pct": 4},
        {"id": "i2", "type": "vo2max", "duration_s": 3500, "np_watts": 285, "decoupling_pct": 5},
        {"id": "i3", "type": "vo2max", "duration_s": 3700, "np_watts": 292, "decoupling_pct": 4},
    ]
    findings = analyze(current, history=history)
    assert findings.verdict == "退步"


def test_few_comparables_lowers_confidence():
    current = {"id": "iNow", "type": "threshold", "duration_s": 3600, "np_watts": 280, "decoupling_pct": 5}
    history = [{"id": "i1", "type": "threshold", "duration_s": 3600, "np_watts": 275, "decoupling_pct": 5}]
    findings = analyze(current, history=history)
    assert findings.metrics["confidence"] in ("low", "tentative")
