from src.coach.deep_analyzer.sub_analyzers.pacing import analyze


def test_front_loaded_detected():
    activity = {
        "id": "i1",
        "laps": [
            {"lap_index": 0, "avg_power": 330, "np_power": 345, "duration_s": 300, "type": "work"},
            {"lap_index": 1, "avg_power": 320, "np_power": 330, "duration_s": 300, "type": "work"},
            {"lap_index": 2, "avg_power": 295, "np_power": 305, "duration_s": 300, "type": "work"},
            {"lap_index": 3, "avg_power": 260, "np_power": 270, "duration_s": 300, "type": "work"},
        ],
    }
    findings = analyze(activity, physiology={"cp_watts": 280, "w_prime_joules": 22000})
    assert findings.verdict in ("起步冒进", "后段崩盘")
    assert any("VI" in e[0] or "功率" in e[0] for e in findings.evidence)


def test_steady_pacing_verdict():
    activity = {
        "id": "i2",
        "laps": [
            {"lap_index": i, "avg_power": 300, "np_power": 305, "duration_s": 300, "type": "work"}
            for i in range(4)
        ],
    }
    findings = analyze(activity, physiology={"cp_watts": 280, "w_prime_joules": 22000})
    assert findings.verdict in ("节奏平稳", "均衡分布")
